import logging

from telegram.ext import MessageHandler, CommandHandler
from telegram.ext import Filters
from ptbplugins import Plugins

from utilities import d

logger = logging.getLogger(__name__)

SUBREDDIT_SELECT = 0


@Plugins.add(CommandHandler, command=['rem', 'remove'], pass_user_data=True)
@d.restricted
@d.failwithmessage
@d.pass_subreddit(answer=True)
def delete_sub(_, update, user_data=None, subreddit=None):
    logger.info('/remove command')

    subreddit.delete_instance()

    update.message.reply_html('/r/{s.name} ({s.channel.title}) has gone, you have also exited the configuring mode for this sub'.format(s=subreddit))

    user_data.pop('data', None)
