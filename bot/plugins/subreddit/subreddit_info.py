import logging
import re

from telegram.ext import CommandHandler
from telegram import ParseMode

from database.models import Subreddit
from bot import Plugins
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['sub', 'subinfo'], pass_args=True)
@d.restricted
@d.failwithmessage
def sub_info(bot, update, args):
    logger.info('/sub command (args: %s)', args)

    subreddit_name = args[0]

    if not re.search(r'(?:\/?r\/?)?[\w-]{3,22}', subreddit_name, re.I):
        update.message.reply_text('"{}" is not a valid subreddit name'.format(subreddit_name))
        return

    subreddit = Subreddit.fetch(subreddit_name)
    if not subreddit:
        update.message.reply_text('No "{}" in the database'.format(subreddit_name))
        return

    text = u.model_dict(subreddit, plain_formatted_string=True)
    update.message.reply_text(text, parse_mode=ParseMode.HTML)
