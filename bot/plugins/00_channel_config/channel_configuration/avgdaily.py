import logging

from telegram import Update

from bot.conversation import Status
from database.models import Channel
from database.models import Subreddit
from database.queries import subreddit_job
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_channel
def channelconfig_on_avgdaily_command(update: Update, _, channel: Channel):
    logger.info('/avgdaily command')

    channel_subreddits = Subreddit.linked_to_channel(channel)
    if not channel_subreddits:
        update.message.reply_text("No subreddit linked to this channel")
        return Status.WAITING_CHANNEL_CONFIG_ACTION

    subs_count = len(channel_subreddits)
    subs_list = []
    total = 0.0
    for subreddit in channel_subreddits:
        daily_average, partial = subreddit_job.average_daily_posts(subreddit)
        subs_list.append("{}: {} (partial: {})".format(subreddit.r_name, daily_average, partial))
        total += daily_average

    update.message.reply_html(
        "Average daily posts during the past week ({} subreddits): {}\n\nBreakdown:\n{}".format(
            subs_count,
            total,
            "\n".join(subs_list)
        )
    )

    return Status.WAITING_CHANNEL_CONFIG_ACTION
