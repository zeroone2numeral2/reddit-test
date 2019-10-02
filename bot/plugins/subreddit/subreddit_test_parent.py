import logging

from telegram.ext import CommandHandler
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
def on_subreddit_selected(_, update, subreddit=None):
    logger.info('/sub command: subreddit selected (%s)', update.message.text)

    text = u.model_dict(subreddit, plain_formatted_string=True)
    update.message.reply_html(text, disable_web_page_preview=True, reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_cancel(_, update, user_data):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted/completed', reply_markup=Keyboard.REMOVE)

    user_data.pop('subreddit', None)

    return ConversationHandler.END


@Plugins.add_conversation_hanlder()
def test_sub_selection_conv_handler():
    return SelectSubredditConversationHandler(
        entry_command='testsub',
        states={
            SUBREDDIT_SELECT: [MessageHandler(Filters.text, callback=on_subreddit_selected)],
        },
        fallbacks=[CommandHandler(['cancel', 'done'], on_cancel, pass_user_data=True)]
    )




