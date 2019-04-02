import logging

from telegram.ext import CommandHandler
from telegram import ParseMode

from database.models import Subreddit
from bot import Plugins
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['remsub'], pass_args=True)
@d.restricted
@d.failwithmessage
@d.knownsubreddit
def delete_sub(bot, update, args):
    logger.info('/remsub command (args: %s)', args)

    subreddit_name = args[0]

    subreddit = Subreddit.fetch(subreddit_name)
    subreddit.delete_instance()

    update.message.reply_text('r/{} has gone'.format(subreddit_name), parse_mode=ParseMode.HTML)