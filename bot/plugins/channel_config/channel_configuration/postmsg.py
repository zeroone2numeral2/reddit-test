import logging
import re

from telegram import Update, ParseMode
from telegram.error import BadRequest, TelegramError
from telegram.ext import CallbackContext

from bot.conversation import Status
from database.models import Channel
from utilities import u
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_channel
def channelconfig_on_postmsg_command(update: Update, context: CallbackContext, channel: Channel):
    logger.info('/postmsg command')

    text_to_post = re.search(r"^/postmsg (.+)$", update.message.text_html, re.I | re.M).group(1)

    try:
        posted_message = context.bot.send_message(channel.channel_id, text_to_post, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except (TelegramError, BadRequest) as e:
        error_string = str(e)
        update.message.reply_text("Error while sending the message: {}".format(error_string))
        return Status.WAITING_CHANNEL_CONFIG_ACTION

    text = "<a href=\"{}\">Message posted</a>".format(u.message_link(posted_message))
    update.message.reply_html(text, disable_web_page_preview=True)

    return Status.WAITING_CHANNEL_CONFIG_ACTION
