import logging
import re

from playhouse.shortcuts import model_to_dict
from telegram import Update
from telegram.ext import MessageHandler, CommandHandler, CallbackContext
from telegram.ext import Filters
from telegram.ext import ConversationHandler

from bot import mainbot
from bot.conversation import Status
from bot.customfilters import CustomFilters
from database.models import Subreddit
from database.models import Style
from bot.markups import Keyboard
from utilities import u
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation
def on_style_command(update: Update, context: CallbackContext):
    logger.debug('/style: selecting subreddit, text: %s', update.message.text)

    name_filter = context.args[0].lower() if context.args else None

    styles: [Style] = Style.get_list(name_filter=name_filter)
    if not styles:
        update.message.reply_text('Cannot find any style (filter: {})'.format(name_filter))
        return ConversationHandler.END

    buttons_list = [style.name for style in styles]
    reply_markup = Keyboard.from_list(buttons_list)

    update.message.reply_text('Select the style (or /cancel):', reply_markup=reply_markup)

    return Status.SUBREDDIT_SELECT


@d.restricted
@d.failwithmessage
@d.logconversation
def on_cancel_command(update: Update, context: CallbackContext):
    logger.info('/cancel command')

    context.user_data.pop('data', None)

    update.message.reply_html('Operation canceled', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
@d.logconversation
def on_timeout(update: Update, context: CallbackContext):
    logger.debug('conversation timeout')

    context.user_data.pop('data', None)

    update.message.reply_text('Timeout: exited styles configuration')

    return ConversationHandler.END


mainbot.add_handler(ConversationHandler(
    entry_points=[CommandHandler(['style'], on_style_command)],
    states={
        ConversationHandler.TIMEOUT: [MessageHandler(Filters.all, on_timeout)]
    },
    fallbacks=[CommandHandler(['canxcel', 'end', 'exit'], on_cancel_command)],
    conversation_timeout=15 * 60
))
