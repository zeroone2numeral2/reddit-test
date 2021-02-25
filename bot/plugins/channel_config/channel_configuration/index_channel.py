import logging

from telegram import Update

from bot.conversation import Status
from database.models import Channel
from database.models import Subreddit
from utilities import u
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_channel
def channelconfig_on_unposted_command(update: Update, _, channel: Channel):
    logger.info('/unposted command')

    channel.notified_on = None
    channel.save()

    update.message.reply_html("Channel marked as unposted")

    return Status.WAITING_CHANNEL_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_channel
def channelconfig_on_private_command(update: Update, _, channel: Channel):
    logger.info('/private command')

    channel.public = False
    channel.save()

    update.message.reply_html("Channel marked as private (will <b>not</b> be posted in the index channel)")

    return Status.WAITING_CHANNEL_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_channel
def channelconfig_on_public_command(update: Update, _, channel: Channel):
    logger.info('/public command')

    channel.public = True
    channel.save()

    update.message.reply_html("Channel marked as public (will be posted in the index channel)")

    return Status.WAITING_CHANNEL_CONFIG_ACTION


_COMMANDS = ["public", "private", "unposted"]
