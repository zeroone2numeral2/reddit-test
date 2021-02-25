import logging

from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from bot.conversation import Status
from database.models import Subreddit
from database.queries import flairs
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_subreddit
def subconfig_on_flairs_command(update: Update, context: CallbackContext, subreddit: Subreddit):
    logger.info('/flairs command')

    if subreddit.template_has_hashtag("#{ascii_flair}"):
        has_hashtag_text = "This sub's template could include flairs hashtags"
    else:
        has_hashtag_text = "This sub's template can't include flairs hashtags"

    update.message.reply_text(has_hashtag_text)

    flairs_list = flairs.get_flairs(subreddit.name)
    if not flairs_list:
        update.message.reply_text("No flairs saved for this sub")
        return Status.WAITING_SUBREDDIT_CONFIG_ACTION

    hashtag_list = "\n".join(["#" + flair for flair in flairs_list])
    update.message.reply_text(hashtag_list)

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION
