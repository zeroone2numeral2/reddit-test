import logging

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from ptbplugins import Plugins

from utilities import d

logger = logging.getLogger(__name__)

SUBREDDIT_SELECT = 0


@Plugins.add(CommandHandler, command=['rem', 'remove'], pass_user_data=True)
@d.restricted
@d.failwithmessage
@d.pass_subreddit(answer=True)
def delete_sub(update: Update, context: CallbackContext, subreddit=None):
    logger.info('/remove command')

    subreddit.delete_instance()

    update.message.reply_html('/r/{s.name} ({s.channel.title}) has gone, you have also exited the configuring mode for this sub'.format(s=subreddit))

    context.user_data.pop('data', None)
