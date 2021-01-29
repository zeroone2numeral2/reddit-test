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

    days = 7

    if context.args and context.args[0].isdigit():
        days = int(context.args[0])

    depths = subreddit_job.top_fontpage_depth(subreddit, days)
    if not depths:
        update.message.reply_text("No data for this sub")
        return Status.WAITING_SUBREDDIT_CONFIG_ACTION

    depths_strings = []
    max_depth = 0
    for row in depths:
        if row['depth'] == 0:
            # skip the row with "0". The index count starts from 1
            # This is just for legacy support: rows with 0 are simply JobResult
            # objects of jobs that did not result in any submission to post
            # also now when a job did result in nothing to post, the JobResult row will show NULL as depth
            continue

        # print('day:', row['day'], 'depth:', row['depth'], 'times:', row['times'])
        string = "<b>{depth}</b>, x{times} times".format(**row)
        depths_strings.append(string)

        if row['depth'] > max_depth:
            max_depth = row['depth']

    text = "Max frontpage depth reached while processing the subreddit's submissions:\n\n{}\n\nMax: <b>{}</b>\nDuring: {} days".format(
        "\n".join(depths_strings),
        max_depth,
        days
    )
    update.message.reply_html(text)

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION
