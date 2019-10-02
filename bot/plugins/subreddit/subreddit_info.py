import logging

from telegram.ext import MessageHandler
from telegram.ext import Filters
from telegram.ext import ConversationHandler
from ptbplugins import Plugins

from ...select_subreddit_conversationhandler import SelectSubredditConversationHandler
from bot.markups import Keyboard
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)

SUBREDDIT_SELECT = range(1)


@d.restricted
@d.failwithmessage
@SelectSubredditConversationHandler.pass_subreddit
def on_subreddit_selected(_, update, subreddit):
    logger.info('/sub command: subreddit selected (%s)', update.message.text)

    text = u.model_dict(subreddit, plain_formatted_string=True)
    update.message.reply_html(text, disable_web_page_preview=True, reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@Plugins.add_conversation_hanlder()
def info_subreddit_conv_hanlder():
    conv_handler = SelectSubredditConversationHandler(
        entry_command=['sub', 'info'],
        states={
            SUBREDDIT_SELECT: [
                MessageHandler(Filters.text, callback=on_subreddit_selected)
            ],
        }
    )

    return conv_handler
