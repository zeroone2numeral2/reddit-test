import logging

from telegram import Update
from telegram.ext import CallbackContext

from bot.conversation import Status
from database.models import Channel
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_channel
def channelconfig_on_enable_command(update: Update, context: CallbackContext, channel: Channel):
    logger.info('/enable command')

    if channel.enabled:
        update.message.reply_html("Channel already enabled")
        return Status.WAITING_CHANNEL_CONFIG_ACTION

    channel.enable()

    update.message.reply_html("Channel enabled")

    return Status.WAITING_CHANNEL_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_channel
def channelconfig_on_disable_command(update: Update, context: CallbackContext, channel: Channel):
    logger.info('/disable command')

    if not channel.enabled:
        update.message.reply_html("Channel already disabled")
        return Status.WAITING_CHANNEL_CONFIG_ACTION

    channel.disable()

    update.message.reply_html("Channel disabled")

    return Status.WAITING_CHANNEL_CONFIG_ACTION
