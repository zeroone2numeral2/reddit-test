import logging

from telegram.ext import MessageHandler
from telegram.ext import Filters
from ptbplugins import Plugins

from ...select_subreddit_conversationhandler import SelectSubredditConversationHandler
from bot.markups import Keyboard
from utilities import d

logger = logging.getLogger(__name__)

SUBREDDIT_SELECT = 0


@d.restricted
@d.failwithmessage
@SelectSubredditConversationHandler.pass_subreddit
def delete_sub(_, update, args=[], subreddit=None):
    logger.info('/remsub command (args: %s)', args)

    subreddit.delete_instance()

    update.message.reply_html('/r/{s.name} ({s.channel.title}) has gone'.format(s=subreddit), reply_markup=Keyboard.REMOVE)

    return SelectSubredditConversationHandler.END


@Plugins.add_conversation_hanlder()
def remove_subreddit_conv_hanlder():
    conv_handler = SelectSubredditConversationHandler(
        entry_command='remsub',
        states={
            SUBREDDIT_SELECT: [
                MessageHandler(Filters.text, callback=delete_sub)
            ],
        }
    )

    return conv_handler
