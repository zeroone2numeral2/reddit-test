import logging

from telegram.ext import ConversationHandler
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters
from ptbplugins import Plugins

from database.models import Channel
from database.models import Subreddit
from bot.markups import Keyboard
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)

CHANNEL_SELECT = range(1)


@d.restricted
@d.failwithmessage
def on_set_channel_command(_, update, args, user_data):
    logger.info('/subchannel command, args: %s', args)
    
    if not args:
        update.message.reply_text('Usage: /subchannel [sub name]')
        return ConversationHandler.END
    
    subreddit_name = u.normalize_sub_name(args[0])
    
    subreddit = Subreddit.fetch(subreddit_name)
    if not subreddit:
        logger.info('subreddit %s does not exist in the database', subreddit_name)
        update.message.reply_text('Subreddit "r/{}" is not in the database, use /addsub to add one'.format(subreddit_name))
        return ConversationHandler.END

    channels_list = Channel.get_list()
    if not channels_list:
        update.message.reply_text('No saved channel. Use /addchannel to add a channel')
        return ConversationHandler.END

    user_data['subreddit_peewee_obj'] = subreddit

    reply_markup = Keyboard.from_list(channels_list)
    update.message.reply_text('Select the subreddit channel (or /cancel):', reply_markup=reply_markup)

    return CHANNEL_SELECT


@d.restricted
@d.failwithmessage
def on_channel_selected(_, update, user_data):
    logger.info('channel selected: %s', update.message.text)

    channel_id = u.expand_channel_id(update.message.text)
    channel = Channel.get(Channel.channel_id == channel_id)

    subreddit = user_data.pop('subreddit_peewee_obj')
    subreddit.channel = channel
    subreddit.save()

    update.message.reply_text('r/{}\'s channel saved: {}'.format(subreddit.name, channel.title), reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_cancel(_, update):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_channel_selected_incorrect(_, update):
    logger.info('unexpected message while selecting channel')
    update.message.reply_text('Select a channel, or /cancel')

    return CHANNEL_SELECT


@Plugins.add_conversation_hanlder()
def setchannel_conv_hanlder():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler(
            command=['subchannel', 'setchannel'],
            callback=on_set_channel_command,
            pass_args=True,
            pass_user_data=True
        )],
        states={
            CHANNEL_SELECT: [
                MessageHandler(Filters.text & Filters.regex(r'\d+\.\s.+'), callback=on_channel_selected,
                               pass_user_data=True),
                MessageHandler(~Filters.command & Filters.all, callback=on_channel_selected_incorrect),
            ]
        },
        fallbacks=[
            CommandHandler('cancel', on_cancel)
        ]
    )

    return conv_handler
