import logging

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from utilities import u
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['info'])
@d.restricted
@d.failwithmessage
@d.pass_subreddit(answer=True)
def on_subreddit_selected(_, update, subreddit):
    logger.info('/info command')

    text = u.model_dict(subreddit, plain_formatted_string=True)
    update.message.reply_html(text, disable_web_page_preview=True)
