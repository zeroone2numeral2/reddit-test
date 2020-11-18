import logging

from telegram import Update
from telegram.ext import ConversationHandler, CallbackContext

from bot import mainbot
from bot.conversation import Status
from bot.markups import Keyboard
from database.models import Channel
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def channel_selection_handler(update: Update, context: CallbackContext):
    logger.info('%s command', update.message.text)

    channels_list = Channel.get_list()
    if not channels_list:
        update.message.reply_text('No saved channel. Use /addchannel to add a channel')
        return ConversationHandler.END

    if len(context.args) > 0:
        channel_title_filter = context.args[0].lower()
        channels_list = [c for c in channels_list if channel_title_filter in c.lower()]

    reply_markup = Keyboard.from_list(channels_list)
    update.message.reply_text('Select the channel (or /cancel):', reply_markup=reply_markup)

    return Status.CHANNEL_SELECTED


@d.restricted
@d.failwithmessage
@d.logconversation
def on_waiting_channel_selection_unknown_message(update: Update, context: CallbackContext):
    logger.info('WAITING_CHANNEL_SELECTION: unknown action')

    update.message.reply_html(
        "Sorry, I don't understand what you're trying to do. Select a channel or use /cancel to cancel the operation"
    )

    return Status.WAITING_CHANNEL_SELECTION
