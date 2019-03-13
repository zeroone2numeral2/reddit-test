import logging
import re
from pprint import pformat

from playhouse.shortcuts import model_to_dict
from telegram.ext import ConversationHandler
from telegram.ext import MessageHandler
from telegram.ext import RegexHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.error import BadRequest
from telegram.error import TelegramError
from telegram import ParseMode

from database.models import Subreddit
from bot import Plugins
from utilities import u

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['sub'], pass_args=True)
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

    subreddit_dict = model_to_dict(subreddit)

    text = '\n'.join('{}: {}'.format(k, v) for k, v in subreddit_dict.items())

    update.message.reply_text('<code>{}</code>'.format(u.escape(text)), parse_mode=ParseMode.HTML)
