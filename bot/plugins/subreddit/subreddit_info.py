import logging

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from bot import mainbot
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)


@d.restricted
@d.failwithmessage
@d.pass_subreddit(answer=True)
def on_subreddit_selected(update: Update, _, subreddit):
    logger.info('/info command')

    text = u.model_dict(subreddit, plain_formatted_string=True)
    update.message.reply_html(text, disable_web_page_preview=True)


mainbot.add_handler(CommandHandler(['info'], on_subreddit_selected))
