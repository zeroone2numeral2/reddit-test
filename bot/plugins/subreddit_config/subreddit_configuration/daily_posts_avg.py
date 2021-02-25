import logging

from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from bot.conversation import Status
from database.models import Subreddit
from database.queries import subreddit_job
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_subreddit
def subconfig_on_avgdaily_command(update: Update, context: CallbackContext, subreddit: Subreddit):
    logger.info('/avgdaily command')

    daily_average, partial = subreddit_job.average_daily_posts(subreddit)
    update.message.reply_text("Last 7 days' average daily posts: {} (partial: {})".format(daily_average, partial))

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION
