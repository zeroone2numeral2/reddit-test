import logging

from telegram.ext import ConversationHandler
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import CallbackContext
from telegram import Update

from bot import mainbot
from bot.conversation import Status
from bot.customfilters import CustomFilters
from bot.markups import Keyboard, InlineKeyboard
from database.models import Channel, Style
from database.models import Subreddit
from reddit import Reddit, creds
from utilities import u
from utilities import d
from config import config

logger = logging.getLogger('handler')

VALID_SUB_REGEX = r'(?:\/?r\/?)?([\w-]{3,22})'


@d.restricted
@d.failwithmessage
@d.logconversation()
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

    account = creds.default_account
    reddit = Reddit(**account.creds_dict(), **account.default_client.creds_dict())
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

    if len(context.args) > 2:
        channel_title_filter = context.args[2].lower()
        channels_list = [c for c in channels_list if channel_title_filter in c.lower()]

    reply_markup = Keyboard.from_list(channels_list)
    update.message.reply_text(
        'Select the subreddit channel (you can /cancel the operation or /skip the channel selection):',
        reply_markup=reply_markup
    )

    return Status.CHANNEL_SELECT


@d.restricted
@d.failwithmessage
@d.logconversation()
def on_channel_selected(update: Update, context: CallbackContext):
    logger.info('channel selected: %s', update.message.text)

    channel = None
    if update.message.text != '/skip':
        channel_id = u.expand_channel_id(update.message.text)
        logger.info('channel_id: %d', channel_id)
        channel = Channel.get(Channel.channel_id == channel_id)
    else:
        logger.info('multireddit will not be associated to a channel')

    multireddit_name = context.user_data.pop('name')
    redditor = context.user_data.pop('redditor')
    logger.debug('testing subreddit to fetch its id: %s', multireddit_name)

    logger.info('saving multireddit...')
    subreddit = Subreddit.create(
        subreddit_id='{}:{}'.format(redditor, multireddit_name),
        channel=channel,
        name=multireddit_name,
        is_multireddit=True,
        multireddit_owner=redditor,
        style=Style.get_default(),
        test=config.telegram.get('testing', False)
    )

    update.message.reply_text('Saving multireddit...', reply_markup=Keyboard.REMOVE)
    update.message.reply_text(
        'm/{} saved (channel: {})'.format(multireddit_name, channel.title),
        reply_markup=InlineKeyboard.configure_subreddit(subreddit.id)
    )

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
@d.logconversation()
def on_cancel(update: Update, _):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


mainbot.add_handler(ConversationHandler(
    name="multireddit_add",
    entry_points=[
        CommandHandler(['addmulti'], on_addmulti_command, filters=~CustomFilters.ongoing_conversation)],
    states={
        Status.CHANNEL_SELECT: [
            MessageHandler(Filters.regex(r'^\d+') | Filters.regex(r'^/skip$'), on_channel_selected)
        ]
    },
    fallbacks=[
        CommandHandler('cancel', on_cancel)
    ]
), group=-1)
