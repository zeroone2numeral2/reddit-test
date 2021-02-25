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
def channelconfig_on_unlinksubs_command(update: Update, _, channel: Channel):
    logger.info('/unlibksubs command')

    channel_subreddits = Subreddit.linked_to_channel(channel)
    if not channel_subreddits:
        update.message.reply_text("No subreddit linked to this channel")
        return Status.WAITING_CHANNEL_CONFIG_ACTION

    unlinked_subs = []
    for subreddit in channel_subreddits:
        unlinked_subs.append(subreddit.r_name)
        subreddit.channel = None
        subreddit.save()
        logger.debug('removed bind channel for subreddit %s', subreddit.r_name)

    update.message.reply_html("Subreddits unlinked: {}".format(", ".join(unlinked_subs)), disable_web_page_preview=True)

    return Status.WAITING_CHANNEL_CONFIG_ACTION
