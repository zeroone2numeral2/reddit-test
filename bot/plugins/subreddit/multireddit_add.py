import logging

from telegram.ext import ConversationHandler
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import CallbackContext
from telegram import Update

from bot import mainbot
from bot.markups import Keyboard
from database.models import Channel
from database.models import Subreddit
from reddit import reddit
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)

CHANNEL_SELECT = range(1)

VALID_SUB_REGEX = r'(?:\/?r\/?)?([\w-]{3,22})'


@d.restricted
@d.failwithmessage
def on_addmulti_command(update: Update, context: CallbackContext):
    logger.info('/addmultib command, args: %s', str(context.args))
    if len(context.args) < 2:
        update.message.reply_text('Usage: /addmulti [owner] [multireddit name]')
        return ConversationHandler.END

    multireddit_name = context.args[1]
    redditor = context.args[0]

    clean_name = u.normalize_sub_name(multireddit_name)
    if not clean_name:
        update.message.reply_text('"{}" is not a valid multireddit name, or is not public'.format(multireddit_name))
        return ConversationHandler.END

    multireddit_name = clean_name

    name_from_request = reddit.multireddit_exists(redditor, multireddit_name)
    if not name_from_request:
        logger.info('non existing subreddit: %s', multireddit_name)
        update.message.reply_text('"m/{}" does not seem to exist (redditor: {})'.format(multireddit_name, redditor))
        return ConversationHandler.END
    else:
        multireddit_name = name_from_request  # reddit.subreddit_exists() returns the correct name

    channels_list = Channel.get_list()
    if not channels_list:
        update.message.reply_text('No saved channel. Use /addchannel to add a channel')
        return ConversationHandler.END

    context.user_data['name'] = multireddit_name
    context.user_data['redditor'] = redditor

    reply_markup = Keyboard.from_list(channels_list)
    update.message.reply_text('Select the subreddit channel (or /cancel):', reply_markup=reply_markup)

    return CHANNEL_SELECT


@d.restricted
@d.failwithmessage
def on_channel_selected(update: Update, context: CallbackContext):
    logger.info('channel selected: %s', update.message.text)

    channel_id = u.expand_channel_id(update.message.text)
    logger.info('channel_id: %d', channel_id)
    channel = Channel.get(Channel.channel_id == channel_id)

    multireddit_name = context.user_data.pop('name')
    redditor = context.user_data.pop('redditor')
    logger.debug('testing subreddit to fetch its id: %s', multireddit_name)

    logger.info('saving multireddit...')
    Subreddit.create(
        subreddit_id='{}:{}'.format(redditor, multireddit_name),
        channel=channel,
        name=multireddit_name,
        is_multireddit=True,
        multireddit_owner=redditor
    )

    update.message.reply_text('m/{} saved (channel: {})'.format(multireddit_name, channel.title), reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_cancel(update: Update, _):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


mainbot.add_handler(ConversationHandler(
    entry_points=[
        CommandHandler(command=['addmulti'], callback=on_addmulti_command, pass_args=True, pass_user_data=True)],
    states={
        CHANNEL_SELECT: [
            MessageHandler(Filters.text, callback=on_channel_selected, pass_user_data=True)
        ]
    },
    fallbacks=[
        CommandHandler('cancel', on_cancel)
    ]
))
