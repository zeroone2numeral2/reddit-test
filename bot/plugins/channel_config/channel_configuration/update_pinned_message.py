import logging

# noinspection PyPackageRequirements
from telegram import ParseMode, Update
from telegram.ext import CallbackContext
from telegram.error import BadRequest
from telegram.error import TelegramError

from bot.conversation import Status
from bot.markups import Keyboard
from database.models import Channel
from database.models import Subreddit
from database.queries import flairs
from database.queries import subreddit_job
from reddit import Reddit, creds
from utilities import u
from utilities import d
from config import config

logger = logging.getLogger('handler')

SUBREDDIT_URL = 'https://reddit.com/r/{name}/'

MULTIREDDIT_URL = 'https://old.reddit.com/user/{redditor}/m/{name}/'

BASE_POST = """••• <a href="{url}">{name}</a>{multi_subs}{hashtag_placeholder}
• {number_of_posts} {posts_string} every ~{pretty_time} from <code>/{sorting}/</code>\
{quiet_block}\
{ignored_block}"""

BASE_RESUME = """••• <a href="{url}">{name}</a>{multi_subs}{hashtag_placeholder}
•️ top {number_of_posts} {posts_string} from <code>/{sorting}/</code> every {period} at {hour} UTC{weekday_block}\
{ignored_block}"""

HEADER = '<b>This channel tracks the following subreddits</b>:'

FOOTER = """- number of daily posts: <b>~{}</b>
- more subreddit mirrors: @{}"""

ADDITIONAL_FOOTER_PRIVATE_CHANNEL = """- this channel's invite link <a href="{}">here</a>"""

ADDITIONAL_FOOTER_SHORT_INFO_LEGEND = """<b>Legend</b>:
<code>#</code>: current position on the sub's frontpage (based on the sub sorting)
<code>v</code>: current score (upvotes)
<code>c</code>: number of comments
<code>%</code>: upvotes ratio
<code>d/h/m</code>: thread age"""

ADDITIONAL_FOOTER_FLAIRS = """<b>Flairs</b>:
{}"""

WEEKDAYS = (
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday'
)


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_channel
def channelconfig_on_updatepin_command(update: Update, context: CallbackContext, channel: Channel):
    logger.info("/updatepin")

    channel_id = channel.channel_id
    subreddits = Subreddit.select().join(Channel).where(Channel.channel_id == channel_id, Subreddit.enabled == True)

    if not subreddits:
        update.message.reply_text('No subreddit for this channel')
        return Status.WAITING_CHANNEL_CONFIG_ACTION

    subs_info_list = []
    flairs_list = []
    total_number_of_daily_posts = 0.0
    include_short_template_legend_footer = False
    for i, subreddit in enumerate(subreddits):
        if not subreddit.enabled:
            continue

        format_dict = dict(
            name=subreddit.r_name,
            number_of_posts=subreddit.number_of_posts if subreddit.number_of_posts > 1 else 'one',
            posts_string='post' if subreddit.number_of_posts == 1 else 'posts',
            pretty_time=u.pretty_time(subreddit.max_frequency),
            sorting=subreddit.sorting_pretty,
            url=subreddit.subreddit_link,
            sub_multi_prefix=subreddit.prefix,
            hashtag_placeholder='',
            ignored_block='',
            quiet_block='',
            min_score_block='',
            nsfw_spoiler_block='',
            ignore_if_newer_block='',
            multi_subs='',
            # i=i + 1
        )

        if subreddit.is_multireddit:
            if subreddit.template_has_hashtag():
                # decide how to prefix the multireddit's subreddits list
                sub_prefix = '#'
            else:
                sub_prefix = '/r/'

            account = creds.default_account
            reddit = Reddit(**account.creds_dict(), **account.default_client.creds_dict())
            multireddit_subreddits = reddit.multi_subreddits(subreddit.multireddit_owner, subreddit.name)
            format_dict['multi_subs'] = ' ({first_sub_prefix}{subs_list})'.format(
                first_sub_prefix=sub_prefix,
                subs_list=', {}'.format(sub_prefix).join(multireddit_subreddits)
            )

        # this is done both for posts jobs and resume jobs
        if subreddit.allow_nsfw == False or subreddit.hide_spoilers or subreddit.ignore_if_newer_than or subreddit.min_score:
            ignored_list = list()
            if not subreddit.allow_nsfw:
                ignored_list.append('NSFW')
            if subreddit.hide_spoilers:
                ignored_list.append('spoilers')
            if subreddit.ignore_if_newer_than:
                ignored_list.append('submissions newer than ' + u.pretty_time(subreddit.ignore_if_newer_than, sep=' and '))
            if subreddit.min_score:
                ignored_list.append('submissions with less than {} votes'.format(subreddit.min_score))
            if subreddit.ignore_flairless:
                ignored_list.append('flair-less submissions')
            if subreddit.min_upvote_perc:
                ignored_list.append('submissions with an upvotes ratio lower than {}%'.format(subreddit.min_upvote_perc))
            format_dict['ignored_block'] = '\n• ignored submissions: {}'.format(', '.join(ignored_list))

        if not subreddit.is_multireddit and subreddit.template_has_hashtag():
            # we do not do this with multireddits because we decide whether to use
            # hashtags or not to list its subreddit above
            format_dict['hashtag_placeholder'] = ' (#{})'.format(subreddit.name)

        if subreddit.quiet_hours_demultiplier > 1 or subreddit.quiet_hours_demultiplier == 0:
            format_dict['quiet_block'] = '\n• less frequent posts (frequency x{}) from {} to {} UTC'.format(
                subreddit.quiet_hours_demultiplier,
                subreddit.quiet_hours_start or config.quiet_hours.start,
                subreddit.quiet_hours_end or config.quiet_hours.end
            )

        subs_info_list.append(BASE_POST.format(**format_dict))

        average_daily_posts, partial = subreddit_job.average_daily_posts(subreddit)
        if partial:  # use the average if we have a full week of data, otherwise calculate it
            try:
                total_number_of_daily_posts += subreddit.daily_posts
            except Exception as e:
                logger.error('error while calculating number of daily posts for subreddit %s: %s', subreddit.name, str(e), exc_info=True)
                total_number_of_daily_posts += average_daily_posts  # use the average anyway if calculation fails
        else:
            total_number_of_daily_posts += average_daily_posts

        if subreddit.style.name.startswith('short_'):
            # this will let us decide whether to add the abbreviations legend at the bottom
            include_short_template_legend_footer = True

        if subreddit.template_has_hashtag(["#{ascii_flair}", "#{flair_normalized}"]):
            subreddit_flairs = flairs.get_flairs(subreddit.name)  # duplicates are removed
            flairs_list.extend(subreddit_flairs)
            logger.debug("%s template has flair hashtag (flairs number: %d)", subreddit.r_name, len(subreddit_flairs))
            logger.debug("%s", flairs_list)
        else:
            logger.debug("%s template doesn't have flair hashtag", subreddit.r_name)

    subs_text = '\n\n'.join(subs_info_list)

    channel_obj = context.bot.get_chat(channel_id)

    footer = FOOTER.format(
        round(total_number_of_daily_posts, 1),  # for some reasons this includes too many decimals if we don't round it
        config.telegram.index
    )
    if not channel_obj.username:
        # if the channel is private, add the invite link to the footer
        footer += '\n' + ADDITIONAL_FOOTER_PRIVATE_CHANNEL.format(subreddits[0].channel.invite_link or '')

    text = '{}\n\n{}\n\n\n{}'.format(HEADER, subs_text, footer)

    if include_short_template_legend_footer:
        text += '\n\n{}'.format(ADDITIONAL_FOOTER_SHORT_INFO_LEGEND)

    if flairs_list:
        logger.debug("%d flairs", len(flairs_list))
        flairs_list = u.remove_duplicates(flairs_list)
        flairs_list_hashtags = ["#" + flair for flair in flairs_list]
        flairs_list_text = "\n".join(flairs_list_hashtags)
        text += '\n\n{}'.format(ADDITIONAL_FOOTER_FLAIRS.format(flairs_list_text))
    else:
        logger.debug("no flairs")

    if channel_obj.pinned_message:
        # do not try to edit the pinned message if the channel doesn't have one
        try:
            update.message.reply_text('Trying to edit pinned message...')
            channel_obj.pinned_message.edit_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            update.message.reply_markdown('[Message edited]({})'.format(u.message_link(channel_obj.pinned_message)),
                                          reply_markup=Keyboard.REMOVE, disable_web_page_preview=True)
            return Status.WAITING_CHANNEL_CONFIG_ACTION
        except (TelegramError, BadRequest) as e:
            update.message.reply_text('Failed: {}'.format(str(e)))

    try:
        sent_message = context.bot.send_message(channel_id, text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except (BadRequest, TelegramError) as e:
        update.message.reply_text('Error while posting: {}'.format(e.message))
        update.message.reply_text(text, disable_web_page_preview=True)
        return Status.WAITING_CHANNEL_CONFIG_ACTION

    update.message.reply_markdown('[Message sent]({}), pinning...'.format(u.message_link(sent_message)),
                                  reply_markup=Keyboard.REMOVE, disable_web_page_preview=True)

    if channel_obj.pinned_message:
        try:
            channel_obj.pinned_message.delete()
            update.message.reply_text('...old pinned message deleted')
        except (BadRequest, TelegramError) as e:
            logger.warning('could not delete old pinned message: %s', e.message)

    try:
        context.bot.pin_chat_message(channel_id, sent_message.message_id, disable_notification=True)
        update.message.reply_text('...message pinned')
        try:
            # try to delete the "message pinned" service message
            context.bot.delete_message(channel_id, sent_message.message_id + 1)
            update.message.reply_text('...service message deleted')
        except (TelegramError, BadRequest):
            pass
    except (BadRequest, TelegramError) as e:
        update.message.reply_text('...message not pinned: {}'.format(e.message))

    return Status.WAITING_CHANNEL_CONFIG_ACTION
