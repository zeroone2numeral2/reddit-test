import logging

from telegram import Update
from telegram.ext import CallbackContext

from bot.conversation import Status
from database.models import Subreddit
from database.queries import subreddit_job
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_subreddit
def subconfig_on_fpmaxdepth_command(update: Update, context: CallbackContext, subreddit: Subreddit):
    logger.info('/fpmaxdepth command')

    depths = subreddit_job.top_fontpage_depth(subreddit)
    if not depths:
        update.message.reply_text("Not enough data")
        return Status.WAITING_SUBREDDIT_CONFIG_ACTION

    depths_strings = []
    max_depth = 0
    for row in depths:
        print('day:', row['day'], 'depth:', row['depth'], 'times:', row['times'])
        string = "day {day}: <b>{depth}</b> x{times} times".format(**row)
        depths_strings.append(string)

        if row['depth'] > max_depth:
            max_depth = row['depth']

    text = "Max frontpage depth reached while processing the subreddit's submissions:\n\n{}\n\nMax: <b>{}</b>".format(
        "\n".join(depths_strings),
        max_depth
    )
    update.message.reply_html(text)

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION
