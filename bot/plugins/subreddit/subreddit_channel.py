import logging

from telegram.ext import ConversationHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
from ptbplugins import Plugins

from ...select_subreddit_conversationhandler import SelectSubredditConversationHandler
from database.models import Channel
from bot.markups import Keyboard
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)

SUBREDDIT_SELECT, CHANNEL_SELECT = range(2)


@d.restricted
@d.failwithmessage
@SelectSubredditConversationHandler.pass_subreddit
def on_subreddit_selected(_, update, user_data={}, subreddit=None):
    logger.info('subreddit selected: %s', update.message.text)

    user_data['subreddit'] = subreddit

    channels_list = Channel.get_list()
    if not channels_list:
        update.message.reply_text('No saved channel. Use /addchannel to add a channel')
        return ConversationHandler.END

    reply_markup = Keyboard.from_list(channels_list)
    update.message.reply_text(
        'Selected subreddit: /r/{s.name} (channel: {s.channel.title}). Select the new channel, or /cancel:'.format(s=subreddit),
        reply_markup=reply_markup
    )

    return CHANNEL_SELECT


@d.restricted
@d.failwithmessage
def on_channel_selected(_, update, user_data):
    logger.info('channel selected: %s', update.message.text)

    channel_id = u.expand_channel_id(update.message.text)
    channel = Channel.get(Channel.channel_id == channel_id)

    subreddit = user_data.pop('subreddit')
    subreddit.channel = channel
    subreddit.save()

    update.message.reply_text('r/{}\'s channel saved: {}'.format(subreddit.name, channel.title), reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_cancel(_, update, user_data):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted', reply_markup=Keyboard.REMOVE)

    user_data.pop('subreddit', None)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_channel_selected_incorrect(_, update):
    logger.info('unexpected message while selecting channel')
    update.message.reply_text('Select a channel, or /cancel', reply_markup=Keyboard.REMOVE)

    return CHANNEL_SELECT


@Plugins.add_conversation_hanlder()
def setchannel_conv_hanlder():
    conv_handler = SelectSubredditConversationHandler(
        entry_command=['subchannel', 'setchannel'],
        states={
            SUBREDDIT_SELECT: [MessageHandler(Filters.text, callback=on_subreddit_selected, pass_user_data=True)],
            CHANNEL_SELECT: [
                MessageHandler(Filters.text & Filters.regex(r'\d+\.\s.+'), callback=on_channel_selected,
                               pass_user_data=True),
                MessageHandler(~Filters.command & Filters.all, callback=on_channel_selected_incorrect),
            ]
        }
    )

    return conv_handler
