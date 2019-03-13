import logging

from telegram.ext import CommandHandler
from telegram import ParseMode

from database.models import Subreddit
from bot import Plugins
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['delsub'], pass_args=True)
@d.restricted
@d.failwithmessage
def delete_sub(bot, update, args):
    logger.info('/delsub command (args: %s)', args)

    subreddit_name = args[0]

    if not u.normalize_sub_name(subreddit_name):
        update.message.reply_text('"{}" is not a valid subreddit name'.format(subreddit_name))
        return

    subreddit = Subreddit.fetch(subreddit_name)
    if not subreddit:
        update.message.reply_text('No "{}" in the database'.format(subreddit_name))
        return
    
    subreddit.delete_instance()

    update.message.reply_text('r/{} has gone'.format(subreddit_name), parse_mode=ParseMode.HTML)
