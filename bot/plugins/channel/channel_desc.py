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
from utilities import u
from utilities import d
from config import config

logger = logging.getLogger(__name__)

BASE_POST = """{i}) <a href="https://reddit.com/r/{name}">/r/{name}</a>, {number_of_posts} {posts_string} every ~{pretty_time} \
from /{sorting}/{quiet_block}{min_score_block}{nsfw_spoiler_block}{ignored_block}\
"""

BASE_RESUME = """{i}) <a href="https://reddit.com/r/{name}">/r/{name}</a>, top {number_of_posts} {posts_string} from /{sorting}/ \
every {period} at {hour} UTC{weekday_block}\
"""

HEADER = '<b>This channel tracks the following subreddits</b>:'

WEEKDAYS = (
    'Monday',
    'Tuesday',
    'Wednesday',
    'Thursday',
    'Friday',
    'Saturday',
    'Sunday'
)


def pretty_time(total_minutes):
    hours = int(total_minutes / 60)
    minutes = total_minutes - (hours * 60)

    if (minutes % 10) != 0:
        minutes = minutes + (10 - (minutes % 10))
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
            string += ', '

        string += '{} minutes'.format(minutes)

    return string


@Plugins.add(CommandHandler, command=['getdesc', 'setdesc'])
@d.restricted
@d.failwithmessage
def gen_channel_description(bot: Bot, update):
    logger.info('getdesc/setdesc command: %s', update.message.text)

    channel_id = -1001115950415
    subreddits = Subreddit.select().join(Channel).where(Channel.channel_id == channel_id, (Subreddit.enabled == True | Subreddit.enabled_resume == True))

    if not subreddits:
        print('no channel')
        return

    subs_info_list = []
    for i, subreddit in enumerate(subreddits):
        format_dict = dict(
            name=subreddit.name,
            number_of_posts=subreddit.number_of_posts if subreddit.number_of_posts > 1 else 'one',
            posts_string='post' if subreddit.number_of_posts == 1 else 'posts',
            pretty_time=pretty_time(subreddit.max_frequency),
            sorting=subreddit.sorting,
            quiet_block='',
            min_score_block='',
            nsfw_spoiler_block='',
            ignore_if_newer_block='',
            i=i + 1
        )

        if subreddit.allow_nsfw == False or subreddit.hide_spoilers or subreddit.ignore_if_newer_than or subreddit.min_score:
            ignored_list = list()
            if not subreddit.allow_nsfw:
                ignored_list.append('NSFW')
            if subreddit.hide_spoilers:
                ignored_list.append('spoilers')
            if subreddit.ignore_if_newer_than:
                ignored_list.append('submissions newer than ' + pretty_time(subreddit.ignore_if_newer_than))
            if subreddit.min_score:
                ignored_list.append('submissions with less than {} votes'.format(subreddit.min_score))
            format_dict['ignored_block'] = '. Ignored submissions: {}'.format(', '.join(ignored_list))

        if subreddit.sorting in ('top', 'day'):
            format_dict['sorting'] = 'top/day'
        elif subreddit.sorting == 'week':
            format_dict['sorting'] = 'top/week'

        if subreddit.enabled:
            if subreddit.quiet_hours_demultiplier > 1 or subreddit.quiet_hours_demultiplier == 0:
                format_dict['quiet_block'] = '. Less frequent posts (frequency x{}) from {} to {} UTC'.format(
                    subreddit.quiet_hours_demultiplier,
                    subreddit.quiet_hours_start,
                    subreddit.quiet_hours_end
                )

            subs_info_list.append(BASE_POST.format(**format_dict))
        elif subreddit.enabled_resume:
            format_dict['period'] = subreddit.frequency
            format_dict['hour'] = subreddit.hour
            format_dict['weekday_block'] = ''
            if subreddit.frequency == 'week':
                format_dict['weekday_block'] = ' (on {})'.format(WEEKDAYS[subreddit.weekday])

            subs_info_list.append(BASE_RESUME.format(**format_dict))

    subs_text = '\n\n'.join(subs_info_list)
    footer = '<a href="{}">Invite link</a> also in the description. More subreddit mirrors: @{}'.format(
        subreddits[0].channel.invite_link or '',
        config.telegram.index
    )
    text = '{}\n\n{}\n\n{}'.format(HEADER, subs_text, footer)

    sent_message = bot.send_message(channel_id, text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    update.message.reply_markdown('[Message sent]({}), pinning...'.format(u.message_link(sent_message)))

    channel_obj = bot.get_chat(channel_id)
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

    # update.message.reply_html(text, disable_web_page_preview=True)





