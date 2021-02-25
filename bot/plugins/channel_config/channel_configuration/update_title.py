import logging

from telegram import Update
from telegram.error import BadRequest, TelegramError
from telegram.ext import CallbackContext

from bot.conversation import Status
from database.models import Channel
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_channel
def channelconfig_on_updatetitle_command(update: Update, context: CallbackContext, channel: Channel):
    logger.info('/updatechat command')

    try:
        chat = context.bot.get_chat(channel.channel_id)
    except (TelegramError, BadRequest) as e:
        logger.warning('error while getting the chat: %s', e.message)
        update.message.reply_text("Error while fetching the chat: {}".format(e.message))
        return Status.WAITING_CHANNEL_CONFIG_ACTION

    channel.title = chat.title
    channel.username = chat.username
    channel.invite_link = chat.invite_link
    channel.save()

    update.message.reply_html("Chat data updated")

    return Status.WAITING_CHANNEL_CONFIG_ACTION
