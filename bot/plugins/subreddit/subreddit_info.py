import logging

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from database.models import Subreddit
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['sub', 'subinfo', 'info'], pass_args=True)
@d.restricted
@d.failwithmessage
@d.knownsubreddit
def sub_info(_, update, args):
    logger.info('/sub command (args: %s)', args)

    subreddit_name = args[0]
    subreddit = Subreddit.fetch(subreddit_name)

    text = u.model_dict(subreddit, plain_formatted_string=True)
    update.message.reply_html(text, disable_web_page_preview=True)
