import logging

from telegram.ext import ConversationHandler
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.ext import CallbackContext
from telegram import Update

from bot import mainbot
from bot.conversation import Status
from bot.markups import Keyboard
from database.models import Channel
from database.models import Subreddit
from reddit import reddit
from utilities import u
from utilities import d
from config import config

logger = logging.getLogger('handler')

VALID_SUB_REGEX = r'(?:\/?r\/?)?([\w-]{3,22})'


@d.restricted
@d.failwithmessage
@d.logconversation
def on_addsub_command(update: Update, context: CallbackContext):
    logger.info('/addsub command, args: %s', str(context.args))
    if not context.args:
        update.message.reply_text('Usage: /addsub [sub name] <channel title filter>')
        return ConversationHandler.END

    subreddit_name = context.args[0]

    clean_name = u.normalize_sub_name(subreddit_name)
    if not clean_name:
        update.message.reply_text('"{}" is not a valid subreddit name'.format(subreddit_name))
        return ConversationHandler.END

    subreddit_name = clean_name

    name_from_request = reddit.subreddit_exists(subreddit_name)
    if not name_from_request:
        logger.info('non existing subreddit: %s', subreddit_name)
        update.message.reply_text('"r/{}" does not seem to exist'.format(subreddit_name))
        return ConversationHandler.END
    else:
        subreddit_name = name_from_request  # reddit.subreddit_exists() returns the correct name

    """ allow to add the same subreddit multiple times
    if Subreddit.fetch(subreddit_name):
        update.message.reply_html('This sub is already saved (<code>/sub {}</code>)'.format(subreddit_name))
        return ConversationHandler.END
    """

    channels_list = Channel.get_list()
    if not channels_list:
        update.message.reply_text('No saved channel. Use /addchannel to add a channel')
        return ConversationHandler.END

    context.user_data['name'] = subreddit_name

    if len(context.args) > 1:
        channel_title_filter = context.args[1].lower()
        channels_list = [c for c in channels_list if channel_title_filter in c.lower()]

    reply_markup = Keyboard.from_list(channels_list)
    # noinspection SqlNoDataSourceInspection
    text = "Select the subreddit's channel from the list ({}) (you can /cancel the operation or /skip the channel selection)".format(
        'filtered list' if len(context.args) > 1 else 'full list'
    )
    update.message.reply_text(text, reply_markup=reply_markup)

    return Status.CHANNEL_SELECT


@d.restricted
@d.failwithmessage
@d.logconversation
def on_channel_selected(update: Update, context: CallbackContext):
    logger.info('channel selected: %s', update.message.text)

    channel = None
    if update.message.text != '/skip':
        channel_id = u.expand_channel_id(update.message.text)
        logger.info('channel_id: %d', channel_id)
        channel = Channel.get(Channel.channel_id == channel_id)
    else:
        logger.info('subreddit will not be associated to a channel')

    subreddit_name = context.user_data.pop('name')
    logger.debug('testing subreddit to fetch its id: %s', subreddit_name)

    subreddit_id = None
    if subreddit_name.lower() == 'all':
        # r/all is not a real subreddit, so it doesn't have an id. We will use "frontpage" as id
        logger.info('we are adding r/all')
        subreddit_id = 'frontpage'
    else:
        for submission in reddit.subreddit(subreddit_name).new(limit=1):
            # u.print_submission(submission)

            subreddit_name = submission.subreddit
            subreddit_id = submission.subreddit_id
            logger.info('subreddit_id: %s', subreddit_id)
            break

    logger.info('saving subreddit...')
    Subreddit.create(
        subreddit_id=subreddit_id,
        channel=channel,
        name=subreddit_name,
        test=config.telegram.get('testing', False)
    )

    update.message.reply_text(
        'r/{} saved (channel: {})'.format(subreddit_name, channel.title if channel else 'none'),
        reply_markup=Keyboard.REMOVE
    )

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
@d.logconversation
def on_cancel(update: Update, _):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


mainbot.add_handler(ConversationHandler(
    entry_points=[
        CommandHandler(['addsub'], on_addsub_command)],
    states={
        Status.CHANNEL_SELECT: [
            MessageHandler(Filters.regex(r'^\d+') | Filters.regex(r'^/skip$'), on_channel_selected)
        ]
    },
    fallbacks=[
        CommandHandler('cancel', on_cancel)
    ]
))
