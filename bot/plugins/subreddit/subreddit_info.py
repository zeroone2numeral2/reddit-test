import logging
import re

from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
from telegram.ext import ConversationHandler
from ptbplugins import Plugins

from bot.markups import Keyboard
from database.models import Subreddit
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)

SUBREDDIT_SELECT = range(1)


@d.restricted
@d.failwithmessage
def on_sub_command(_, update, args):
    logger.info('/sub command, args: %s', str(args))

    name_filter = args[0] if args else None

    subreddits = Subreddit.get_list(name_filter=name_filter)
    if not subreddits:
        update.message.reply_text('Cannot find any subreddit (filter: {})'.format(name_filter))
        return ConversationHandler.END

    reply_markup = Keyboard.from_list(['{}. /r/{} ({})'.format(s.id, s.name, s.channel.title) for s in subreddits])

    update.message.reply_text('Select the subreddit (or /cancel):', reply_markup=reply_markup)

    return SUBREDDIT_SELECT


@d.restricted
@d.failwithmessage
def on_subreddit_selected(_, update):
    logger.info('/sub command: subreddit selected (%s)', update.message.text)

    subreddit_key = int(re.search(r'(\d+)\. .*', update.message.text, re.I).group(1))
    logger.info('subreddit key: %d', subreddit_key)

    subreddit = Subreddit.get(Subreddit.id == subreddit_key)

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
def info_subreddit_conv_hanlder():
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler(command=['sub', 'info'], callback=on_sub_command, pass_args=True)],
        states={
            SUBREDDIT_SELECT: [
                MessageHandler(Filters.text, callback=on_subreddit_selected)
            ],
        },
        fallbacks=[
            CommandHandler(['cancel', 'done'], on_cancel, pass_user_data=True)
        ]
    )

    return conv_handler
