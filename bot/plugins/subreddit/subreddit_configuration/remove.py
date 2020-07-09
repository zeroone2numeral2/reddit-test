import logging

from telegram import Update
from telegram.ext import CallbackContext, ConversationHandler

from database.models import Subreddit
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_subreddit
def subconfig_on_remove_command(update: Update, context: CallbackContext, subreddit: Subreddit):
    logger.info('/remove command')

    subreddit.delete_instance()

    update.message.reply_html('/r/{s.name} (channel: {title}) has gone, you have also exited the configuring mode for this sub'.format(
        s=subreddit,
        title=subreddit.channel_title()
    ))

    context.user_data.pop('data', None)

    return ConversationHandler.END
