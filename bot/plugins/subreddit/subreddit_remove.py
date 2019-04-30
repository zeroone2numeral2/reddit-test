import logging

from telegram.ext import CommandHandler
from telegram import ParseMode
from ptbplugins import Plugins

from database.models import Subreddit
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['remsub'], pass_args=True)
@d.restricted
@d.failwithmessage
@d.knownsubreddit
def delete_sub(_, update, args):
    logger.info('/remsub command (args: %s)', args)

    subreddit_name = args[0]

    subreddit = Subreddit.fetch(subreddit_name)
    subreddit.delete_instance()

    update.message.reply_text('r/{} has gone'.format(subreddit_name), parse_mode=ParseMode.HTML)
