import logging

from telegram import Update

from bot.conversation import Status
from database.models import Channel
from database.models import Subreddit
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_channel
def channelconfig_on_subs_command(update: Update, _, channel: Channel):
    logger.info('/subs command')

    channel_subreddits = Subreddit.linked_to_channel(channel)
    if not channel_subreddits:
        update.message.reply_text("No subreddit linked to this channel")
        return Status.WAITING_CHANNEL_CONFIG_ACTION

    update.message.reply_html(
        "\n".join(["{}. {}".format(i + 1, s.r_name) for i, s in enumerate(channel_subreddits)])
    )

    return Status.WAITING_CHANNEL_CONFIG_ACTION
