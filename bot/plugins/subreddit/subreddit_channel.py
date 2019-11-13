import logging

from telegram.ext import ConversationHandler, CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
from ptbplugins import Plugins

from database.models import Channel
from bot.markups import Keyboard
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)

SUBREDDIT_SELECT, CHANNEL_SELECT = range(2)


@d.restricted
@d.failwithmessage
@d.pass_subreddit(answer=True)
def select_channel(_, update, *args, **kwargs):
    logger.info('setchannel callback: %s', update.message.text)

    channels_list = Channel.get_list()
    if not channels_list:
        update.message.reply_text('No saved channel. Use /end and /addchannel to add a channel')
        return ConversationHandler.END

    reply_markup = Keyboard.from_list(channels_list)
    update.message.reply_text(
        'Select the new channel, or /cancel:',
        reply_markup=reply_markup
    )

    return CHANNEL_SELECT


@d.restricted
@d.failwithmessage
@d.pass_subreddit()
def on_channel_selected(_, update, subreddit=None):
    logger.info('channel selected: %s', update.message.text)

    channel_id = u.expand_channel_id(update.message.text)
    channel = Channel.get(Channel.channel_id == channel_id)

    subreddit.channel = channel
    subreddit.save()

    update.message.reply_text('r/{}\'s channel saved: {}'.format(subreddit.name, channel.title), reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_channel_selected_incorrect(_, update):
    logger.info('unexpected message while selecting channel')
    update.message.reply_text('Select a channel, or /cancel')

    return CHANNEL_SELECT


@d.restricted
@d.failwithmessage
def on_cancel(_, update):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Okay, we will not change this subreddit\'s channel', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@Plugins.add_conversation_hanlder()
def setchannel_conv_hanlder():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler(command=['setchannel'], callback=select_channel)],
        states={
            SUBREDDIT_SELECT: [MessageHandler(Filters.text, callback=select_channel, pass_user_data=True)],
            CHANNEL_SELECT: [
                MessageHandler(Filters.text & Filters.regex(r'\d+\.\s.+'), callback=on_channel_selected),
                MessageHandler(~Filters.command & Filters.all, callback=on_channel_selected_incorrect),
            ],
        },
        fallbacks=[CommandHandler(['cancel', 'done'], on_cancel)]
    )

    return conv_handler
