import logging

from telegram.ext import ConversationHandler
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram import ParseMode

from bot.markups import Keyboard
from database.models import Channel
from database.models import Subreddit
from bot import Plugins
from reddit import reddit
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)

CHANNEL_SELECT = range(1)

VALID_SUB_REGEX = r'(?:\/?r\/?)?([\w-]{3,22})'


@d.restricted
@d.failwithmessage
def on_addsub_command(_, update, args, user_data):
    logger.info('/addsub command, args: %s', str(args))
    if not args:
        update.message.reply_text('Usage: /addsub [sub name]')
        return ConversationHandler.END

    subreddit_name = args[0]

    clean_name = u.normalize_sub_name(subreddit_name)
    if not clean_name:
        update.message.reply_text('"{}" is not a valid subreddit name'.format(subreddit_name))
        return ConversationHandler.END

    subreddit_name = clean_name

    if not reddit.subreddit_exists(subreddit_name):
        logger.info('non existing subreddit: %s', subreddit_name)
        update.message.reply_text('"r/{}" does not seem to exist'.format(subreddit_name))
        return ConversationHandler.END
    else:
        subreddit_name = reddit.subreddit_exists(subreddit_name)  # also returns the correct name

    if Subreddit.fetch(subreddit_name):
        update.message.reply_text('This sub is already saved (<code>/sub {}</code>)'.format(subreddit_name),
                             parse_mode=ParseMode.HTML)
        return ConversationHandler.END

    channels_list = Channel.get_list()
    if not channels_list:
        update.message.reply_text('No saved channel. Use /addchannel to add a channel')
        return ConversationHandler.END

    user_data['name'] = subreddit_name

    reply_markup = Keyboard.from_list(channels_list)
    update.message.reply_text('Select the subreddit channel (or /cancel):', reply_markup=reply_markup)

    return CHANNEL_SELECT


@d.restricted
@d.failwithmessage
def on_channel_selected(_, update, user_data):
    logger.info('channel selected: %s', update.message.text)

    channel_id = u.expand_channel_id(update.message.text)
    logger.info('channel_id: %d', channel_id)
    channel = Channel.get(Channel.channel_id == channel_id)

    subreddit_name = user_data.pop('name')

    subreddit_id = None
    for submission in reddit.subreddit(subreddit_name).new(limit=1):
        subreddit_name = submission.subreddit
        subreddit_id = submission.subreddit_id
        logger.info('subreddit_id: %s', subreddit_id)
        break

    logger.info('saving subreddit...')
    Subreddit.create(
        subreddit_id=subreddit_id,
        channel=channel,
        name=subreddit_name
    )

    update.message.reply_text('r/{} saved (channel: {})'.format(subreddit_name, channel.title), reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_cancel(_, update):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@Plugins.add_conversation_hanlder()
def addsubreddit_conv_hanlder():
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler(command=['addsub'], callback=on_addsub_command, pass_args=True, pass_user_data=True)],
        states={
            CHANNEL_SELECT: [
                MessageHandler(Filters.text, callback=on_channel_selected, pass_user_data=True)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', on_cancel)
        ]
    )

    return conv_handler
