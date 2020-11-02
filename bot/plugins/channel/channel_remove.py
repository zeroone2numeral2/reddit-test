import logging

from telegram import Update
from telegram.ext import ConversationHandler, CallbackContext
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters

from bot import mainbot
from bot.conversation import Status
from bot.markups import Keyboard
from database.models import Channel
from database.models import Subreddit
from .select_channel import channel_selection_handler
from utilities import u
from utilities import d

logger = logging.getLogger('handler')

VALID_SUB_REGEX = r'(?:\/?r\/?)?([\w-]{3,22})'


@d.restricted
@d.failwithmessage
def on_channel_selected(update, _):
    logger.info('channel selected: %s', update.message.text)

    channel_id = u.expand_channel_id(update.message.text)
    logger.info('channel_id: %d', channel_id)
    channel = Channel.get(Channel.channel_id == channel_id)

    channel_subreddits = Subreddit.linked_to_channel(channel)
    if channel_subreddits:
        for subreddit in channel_subreddits:
            subreddit.channel = None
            subreddit.save()
            logger.debug('removed bind channel for subreddit r/%s', subreddit.name)

    channel_title = channel.title
    
    logger.info('Deleting channel...')
    channel.delete_instance()
    
    update.message.reply_text(
        'Channel "{}" removed. Linked subreddits: {} (if any, their channel as been set to NULL)'.format(
            channel_title,
            ', '.join([s.name for s in channel_subreddits]) if channel_subreddits else 'none'
        ),
        reply_markup=Keyboard.REMOVE
    )

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_cancel(update, _):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


mainbot.add_handler(ConversationHandler(
    entry_points=[CommandHandler(command=['remchannel'], callback=channel_selection_handler)],
    states={
        Status.CHANNEL_SELECTED: [
            MessageHandler(Filters.text & ~Filters.command, callback=on_channel_selected)
        ]
    },
    fallbacks=[
        CommandHandler('cancel', on_cancel)
    ]
))
