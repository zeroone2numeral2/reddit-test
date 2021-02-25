import logging

from telegram import Update

from bot.conversation import Status
from database.models import Channel
from utilities import u
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_channel
def channelconfig_on_info_command(update: Update, _, channel: Channel):
    logger.info('/info command')

    text = u.model_dict(channel, plain_formatted_string=True)
    update.message.reply_html(text, disable_web_page_preview=True)

    return Status.WAITING_CHANNEL_CONFIG_ACTION
