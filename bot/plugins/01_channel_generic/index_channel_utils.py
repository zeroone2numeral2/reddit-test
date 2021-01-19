import logging
import time

from telegram import ParseMode
from telegram.ext import CommandHandler, CallbackContext

from bot import mainbot
from database.queries import channels
from utilities import d
from utilities import u
from config import config

logger = logging.getLogger('handler')

STANDARD_TEXT = """Full list of channels here (pinned message)

<b>Request a subreddit mirror</b>: https://telegra.ph/how-to-03-20"""


@d.restricted
@d.failwithmessage
def on_markallasposted_command(update, context: CallbackContext):
    logger.info('/markallasposted command')

    channels_list = channels.get_channels()
    for channel in channels_list:
        channel.notified_on = u.now()
        channel.save()

    update.message.reply_text("Done, all channels marked as posted")


@d.restricted
@d.failwithmessage
def on_postinindex_command(update, context: CallbackContext):
    logger.info('/postinindex command')

    channels_list = channels.get_channels()
    index_username = '@' + config.telegram.index
    for channel in channels_list:
        if channel.notified_on:
            continue

        logger.info("posting channel: %s", channel.title)
        text = "New channel: <a href=\"{link}\">{title}</a> (mirrors: {subreddits})"
        subs = []
        for subreddit in channel.subreddits:
            subs.append(subreddit.r_inline_link)

        text = text.format(
            link=channel.invite_link,
            title=channel.title,
            subreddits=", ".join(subs)
        )
        context.bot.send_message(index_username, text, disable_web_page_preview=True, parse_mode=ParseMode.HTML)
        channel.notified_on = u.now()
        channel.save()

        time.sleep(3)

    update.message.reply_text("New channels posted in {}".format(index_username))


mainbot.add_handler(CommandHandler('markallasposted', on_markallasposted_command))
mainbot.add_handler(CommandHandler('postinindex', on_postinindex_command))
