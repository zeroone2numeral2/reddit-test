import logging

from telegram.ext import ConversationHandler
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters

from bot.markups import Keyboard
from database.models import Channel
from database.models import Subreddit
from bot import Plugins
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)

CHANNEL_SELECT = range(1)

VALID_SUB_REGEX = r'(?:\/?r\/?)?([\w-]{3,22})'


@d.restricted
@d.failwithmessage
def on_remchannel_command(bot, update):
    logger.info('/remchannel command')

    channels_list = Channel.get_list()
    if not channels_list:
        update.message.reply_text('No saved channel. Use /addchannel to add a channel')
        return ConversationHandler.END

    reply_markup = Keyboard.from_list(channels_list)
    update.message.reply_text('Select the channel (or /cancel):', reply_markup=reply_markup)

    return CHANNEL_SELECT


@d.restricted
@d.failwithmessage
def on_channel_selected(bot, update):
    logger.info('channel selected: %s', update.message.text)

    channel_id = u.expand_channel_id(update.message.text)
    logger.info('channel_id: %d', channel_id)
    channel = Channel.get(Channel.channel_id == channel_id)

    if Subreddit.subreddit_with_channel(channel):
        update.message.reply_text('Sorry, apparently there is one or more subreddits using this channel',
                                  reply_markup=Keyboard.REMOVE)
        return ConversationHandler.END
    
    channel_title = channel.title
    
    logger.info('Deleting channel...')
    channel.delete_instance()
    
    update.message.reply_text('Channel "{}" removed'.format(channel_title), reply_markup=Keyboard.REMOVE)
    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_cancel(bot, update):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


conv_handler = ConversationHandler(
    entry_points=[CommandHandler(command=['remchannel'], callback=on_remchannel_command)],
    states={
        CHANNEL_SELECT: [
            MessageHandler(Filters.text, callback=on_channel_selected)
        ]
    },
    fallbacks=[
        CommandHandler('cancel', on_cancel)
    ]
)


@Plugins.add_conversation_hanlder(conv_handler)
def remchannel_conv_hanlder():
    pass
