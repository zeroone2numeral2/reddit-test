import logging
import os

from telegram import Update
from telegram.ext import CallbackContext

from bot.conversation import Status
from database.models import Channel
from database.models import Subreddit
from bot.markups import Keyboard
from reddit import Reddit, creds
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_channel
def channelconfig_on_seticon_command(update: Update, context: CallbackContext, channel: Channel):
    logger.info('/seticon command')

    channel_subreddits = Subreddit.linked_to_channel(channel)
    if not channel_subreddits:
        update.message.reply_text("No subreddit linked to this channel")
        return Status.WAITING_CHANNEL_CONFIG_ACTION

    account = creds.default_account
    reddit = Reddit(**account.creds_dict(), **account.default_client.creds_dict())

    for subreddit in channel_subreddits:
        file_path = reddit.get_icon(subreddit.name, download=True)
        if not file_path:
            continue

        with open(file_path, 'rb') as f:
            context.bot.set_chat_photo(subreddit.channel.channel_id, f)

        os.remove(file_path)

        update.message.reply_text('Icon updated (sub: {})'.format(subreddit.r_name))
        return Status.WAITING_CHANNEL_CONFIG_ACTION

    update.message.reply_text("None of the linked subreddits has a suitable icon")

    return Status.WAITING_CHANNEL_CONFIG_ACTION
