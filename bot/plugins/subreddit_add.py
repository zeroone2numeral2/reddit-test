import logging
import re

from telegram.ext import ConversationHandler
from telegram.ext import MessageHandler
from telegram.ext import RegexHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters
from telegram.error import BadRequest
from telegram.error import TelegramError
from telegram import ParseMode
from prawcore.exceptions import Redirect

from bot.markups import Keyboard
from database.models import Channel
from database.models import Subreddit
from bot import Plugins
from reddit import reddit

logger = logging.getLogger(__name__)

CHANNEL_SELECT = range(1)

VALID_SUB_REGEX = r'(?:\/?r\/?)?([\w-]{3,22})'


def on_addsub_command(bot, update, args, user_data):
    logger.info('/addsub command, args: %s', str(args))
    if not args:
        update.message.reply_text('Usage: /addsub [sub name]')
        return ConversationHandler.END

    subreddit_name = args[0]

    match = re.search(VALID_SUB_REGEX, subreddit_name, re.I)
    if not match:
        update.message.reply_text('"{}" is not a valid subreddit name'.format(subreddit_name))
        return ConversationHandler.END

    subreddit_name = match.group(1)

    try:
        for submission in reddit.subreddit(subreddit_name).new(limit=1):
            subreddit_name = submission.subreddit  # save teh correct name
    except Redirect as e:
        logger.error('non existing subreddit: %s', str(e))
        update.message.reply_text('"{}" does not seem to exist'.format(subreddit_name))
        return ConversationHandler.END

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


def on_channel_selected(bot, update, user_data):
    logger.info('channel selected: %s', update.message.text)

    channel_id = int(re.search(r'(\d+)\.\s.+', update.message.text).group(1)) * -1
    channel = Channel.get(channel_id == channel_id)

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

    update.message.reply_text('{} saved (channel: {})'.format(subreddit_name, channel.title), reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


def on_cancel(bot, update):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


conv_handler = ConversationHandler(
    entry_points=[CommandHandler(command=['addsub'], callback=on_addsub_command, pass_args=True, pass_user_data=True)],
    states={
        CHANNEL_SELECT: [
            MessageHandler(Filters.text, callback=on_channel_selected, pass_user_data=True)
        ]
    },
    fallbacks=[
        CommandHandler('cancel', on_cancel)
    ]
)


@Plugins.add_conversation_hanlder(conv_handler)
def addsubreddit_conv_hanlder():
    # serve solo a registrare il ConversationHanlder già inizializzato in maniera più semplice
    # Il nome di questa funzione serve è indicativo, ma serve solo al logging
    pass
