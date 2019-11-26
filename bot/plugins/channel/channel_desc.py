import logging

# noinspection PyPackageRequirements
from telegram import Bot
from telegram import ParseMode
from telegram.ext import ConversationHandler
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
from telegram.ext import CallbackQueryHandler
from telegram.ext import Filters
from telegram.error import BadRequest
from telegram.error import TelegramError
from ptbplugins import Plugins

from bot.markups import Keyboard
from bot.markups import InlineKeyboard
from database.models import Channel
from database.models import Subreddit
from reddit import reddit
from utilities import u
from utilities import d
from config import config

logger = logging.getLogger(__name__)

CHANNEL_SELECT = range(1)

SUBREDDIT_URL = 'https://reddit.com/r/{name}/'

MULTIREDDIT_URL = 'https://old.reddit.com/user/{redditor}/m/{name}/'

BASE_POST = """📌 <a href="{url}">/{sub_multi_prefix}/{name}</a>{multi_subs}{hashtag_placeholder}
⚡️{number_of_posts} {posts_string} every ~{pretty_time} from <code>/{sorting}/</code>\
{quiet_block}\
{ignored_block}"""

BASE_RESUME = """📌 <a href="{url}">/{sub_multi_prefix}/{name}</a>{multi_subs}{hashtag_placeholder}
⚡️ top {number_of_posts} {posts_string} from <code>/{sorting}/</code> every {period} at {hour} UTC{weekday_block}\
{ignored_block}"""

HEADER = '<b>This channel tracks the following subreddits</b>:'

FOOTER = """📬 Number of daily posts: <b>~{}</b>
📣 More subreddit mirrors: @{}"""

ADDITIONAL_FOOTER_PRIVATE_CHANNEL = """🔗 This channel's invite link <a href="{}">here</a>"""

WEEKDAYS = (
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday'
)


def pretty_time(total_minutes, sep=', ', round_by=10):
    """Pretty string representation of minutes

    :param total_minutes: time in minutes
    :param sep: string that separates hours and minutes (if both present)
    :param round_by: round minutes to the highest multiple of 'round_by' possible
    :return: string
    """

    hours = int(total_minutes / 60)
    minutes = total_minutes - (hours * 60)

    if (minutes % round_by) != 0:
        minutes = minutes + (round_by - (minutes % round_by))
        if minutes == 60:
            minutes = 0
            hours += 1

    string = ''
    if hours > 0:
        if hours > 1:
            string += '{} hours'.format(hours)
        else:
            string += 'one hour'

    if minutes > 0:
        if hours > 0:
            string += sep

        string += '{} minutes'.format(minutes)

    return string


@d.restricted
@d.failwithmessage
def on_setdesc_channel_selected(bot: Bot, update):
    logger.info('setdesc command channel selected: %s', update.message.text)

    channel_id = u.expand_channel_id(update.message.text)
    subreddits = Subreddit.select().join(Channel).where(Channel.channel_id == channel_id, (Subreddit.enabled == True | Subreddit.enabled_resume == True))

    if not subreddits:
        update.message.reply_text('No subreddit in this channel')
        return ConversationHandler.END

    subs_info_list = []
    total_number_of_daily_posts = 0
    for i, subreddit in enumerate(subreddits):
        format_dict = dict(
            name=subreddit.name,
            number_of_posts=subreddit.number_of_posts if subreddit.number_of_posts > 1 else 'one',
            posts_string='post' if subreddit.number_of_posts == 1 else 'posts',
            pretty_time=pretty_time(subreddit.max_frequency),
            sorting=subreddit.sorting,
            hashtag_placeholder='',
            ignored_block='',
            quiet_block='',
            min_score_block='',
            nsfw_spoiler_block='',
            ignore_if_newer_block='',
            multi_subs='',
            # i=i + 1
        )

        ################
        # COMMON PARTS #
        ################

        if subreddit.is_multireddit:
            format_dict['sub_multi_prefix'] = 'm'
            format_dict['url'] = MULTIREDDIT_URL.format(redditor=subreddit.multireddit_owner, name=subreddit.name)

            if (subreddit.template and '#{subreddit}' in subreddit.template) or (subreddit.template_resume and '#{subreddit}' in subreddit.template_resume):
                # decide how to prefix the multireddit's subreddits list
                sub_prefix = '#'
            else:
                sub_prefix = '/r/'

            format_dict['multi_subs'] = ' ({first_sub_prefix}{subs_list})'.format(
                first_sub_prefix=sub_prefix,
                subs_list=', {}'.format(sub_prefix).join(reddit.multi_subreddits(subreddit.multireddit_owner, subreddit.name))
            )
        else:
            format_dict['sub_multi_prefix'] = 'r'
            format_dict['url'] = SUBREDDIT_URL.format(name=subreddit.name)

        # this is done both for posts jobs and resume jobs
        if subreddit.allow_nsfw == False or subreddit.hide_spoilers or subreddit.ignore_if_newer_than or subreddit.min_score:
            ignored_list = list()
            if not subreddit.allow_nsfw:
                ignored_list.append('NSFW')
            if subreddit.hide_spoilers:
                ignored_list.append('spoilers')
            if subreddit.ignore_if_newer_than:
                ignored_list.append('submissions newer than ' + pretty_time(subreddit.ignore_if_newer_than, sep=' and '))
            if subreddit.min_score:
                ignored_list.append('submissions with less than {} votes'.format(subreddit.min_score))
            format_dict['ignored_block'] = '\n🗑 Ignored submissions: {}'.format(', '.join(ignored_list))

        if subreddit.sorting in ('top', 'day'):
            format_dict['sorting'] = 'top/day'
        elif subreddit.sorting == 'week':
            format_dict['sorting'] = 'top/week'

        ######################
        # TYPE-SPECIFIC PART #
        ######################

        if subreddit.enabled:
            if not subreddit.is_multireddit and subreddit.template and '#{subreddit}' in subreddit.template:
                format_dict['hashtag_placeholder'] = ' (#{})'.format(subreddit.name)

            if subreddit.quiet_hours_demultiplier > 1 or subreddit.quiet_hours_demultiplier == 0:
                format_dict['quiet_block'] = '\n💤 Less frequent posts (frequency x{}) from {} to {} UTC'.format(
                    subreddit.quiet_hours_demultiplier,
                    subreddit.quiet_hours_start or config.quiet_hours.start,
                    subreddit.quiet_hours_end or config.quiet_hours.end
                )

            subs_info_list.append(BASE_POST.format(**format_dict))

        elif subreddit.enabled_resume:
            format_dict['i'] = i + 1

            if not subreddit.is_multireddit and subreddit.template_resume and '#{subreddit}' in subreddit.template_resume:
                format_dict['hashtag_placeholder'] = ' (#{})'.format(subreddit.name)

            format_dict['period'] = subreddit.frequency
            format_dict['hour'] = subreddit.hour
            format_dict['weekday_block'] = ''
            if subreddit.frequency == 'week':
                format_dict['weekday_block'] = ' (on {})'.format(WEEKDAYS[subreddit.weekday])

            subs_info_list.append(BASE_RESUME.format(**format_dict))

        try:
            total_number_of_daily_posts += u.number_of_daily_posts(subreddit)
        except Exception as e:
            logger.error('error while calculating number of daily posts for subreddit %s: %s', subreddit.name, str(e))

    subs_text = '\n\n'.join(subs_info_list)

    channel_obj = bot.get_chat(channel_id)

    footer = FOOTER.format(
        total_number_of_daily_posts,
        config.telegram.index
    )
    if not channel_obj.username:
        # if the channel is private, add the invite link to the footer
        footer += '\n' + ADDITIONAL_FOOTER_PRIVATE_CHANNEL.format(subreddits[0].channel.invite_link or '')

    text = '{}\n\n{}\n\n\n{}'.format(HEADER, subs_text, footer)

    if channel_obj.pinned_message:
        # do not try to edit the pinned message if the channel doesn't have one
        try:
            update.message.reply_text('Trying to edit pinned message...')
            channel_obj.pinned_message.edit_text(text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            update.message.reply_markdown('[Message edited]({})'.format(u.message_link(channel_obj.pinned_message)),
                                          reply_markup=Keyboard.REMOVE, disable_web_page_preview=True)
            return
        except (TelegramError, BadRequest) as e:
            update.message.reply_text('Failed: {}'.format(str(e)))

    try:
        sent_message = bot.send_message(channel_id, text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except (BadRequest, TelegramError) as e:
        update.message.reply_text('Error while posting: {}'.format(e.message))
        update.message.reply_text(text, disable_web_page_preview=True)
        return

    update.message.reply_markdown('[Message sent]({}), pinning...'.format(u.message_link(sent_message)),
                                  reply_markup=Keyboard.REMOVE, disable_web_page_preview=True)

    if channel_obj.pinned_message:
        try:
            channel_obj.pinned_message.delete()
            update.message.reply_text('...old pinned message deleted')
        except (BadRequest, TelegramError) as e:
            logger.warning('could not delete old pinned message: %s', e.message)

    try:
        bot.pin_chat_message(channel_id, sent_message.message_id, disable_notification=True)
        update.message.reply_text('...message pinned')
        try:
            # try to delete the "message pinned" service message
            bot.delete_message(channel_id, sent_message.message_id + 1)
            update.message.reply_text('...service message deleted')
        except (TelegramError, BadRequest):
            pass
    except (BadRequest, TelegramError) as e:
        update.message.reply_text('...message not pinned: {}'.format(e.message))

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_setdesc_command(_, update):
    logger.info('/setdesc command')

    channels_list = Channel.get_list()
    if not channels_list:
        update.message.reply_text('No saved channel. Use /addchannel to add a channel')
        return ConversationHandler.END

    reply_markup = Keyboard.from_list(channels_list)
    update.message.reply_text('Select the channel (or /cancel):', reply_markup=reply_markup)

    return CHANNEL_SELECT


@d.restricted
@d.failwithmessage
def on_setdesc_channel_selected_incorrect(_, update):
    logger.info('unexpected message while selecting channel')
    update.message.reply_text('Select a channel, or /cancel')

    return CHANNEL_SELECT


@d.restricted
@d.failwithmessage
def on_setdesc_cancel(_, update):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@Plugins.add_conversation_hanlder()
def setdesc_channel_conv_hanlder():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler(command=['setdesc'], callback=on_setdesc_command)],
        states={
            CHANNEL_SELECT: [
                MessageHandler(Filters.text & Filters.regex(r'\d+\.\s.+'), callback=on_setdesc_channel_selected),
                MessageHandler(~Filters.command & Filters.all, callback=on_setdesc_channel_selected_incorrect),
            ]
        },
        fallbacks=[
            CommandHandler('cancel', on_setdesc_cancel)
        ]
    )

    return conv_handler




