import logging
import re

from telegram import Update
from telegram.ext import ConversationHandler, CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters

from bot import mainbot
from bot.conversation import Status
from bot.markups import Keyboard
from database.models import Subreddit
from utilities import u
from utilities import d

logger = logging.getLogger('handler')

KEYS_TO_COPY = (
    'template',
    'template_no_url',
    'url_button',
    'url_button_template',
    'comments_button',
    'comments_button_template',
    'send_medias',
    'webpage_preview',
    'template_resume'
)


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_subreddit(answer=True)
def on_clonestylefrom_command(update: Update, context: CallbackContext, **kwargs):
    logger.info('/clonestylefrom command, args: %s', str(context.args))

    # we consider the second argument as a filter for the destination subreddit selection keyboard
    name_filter = context.args[0] if context.args else None

    subreddits = Subreddit.get_list(name_filter=name_filter)
    if not subreddits:
        update.message.reply_text('Cannot find any subreddit (filter: {})'.format(name_filter))
        return ConversationHandler.END

    reply_markup = Keyboard.from_list(['{}. /r/{} ({})'.format(s.id, s.name, s.channel.title) for s in subreddits])

    update.message.reply_text('Select the subreddit to copy the style from, or /cancel:', reply_markup=reply_markup)

    return Status.WAITING_ORIGIN_SUBREDDIT


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_subreddit(answer=True)
def on_origin_subreddit_selected(update: Update, _, subreddit=None):
    logger.info('/copystylefrom command: origin subreddit selected (%s)', update.message.text)

    subreddit_key = int(re.search(r'(\d+)\. .*', update.message.text, re.I).group(1))
    logger.info('subreddit key: %d', subreddit_key)
    origin_sub = Subreddit.get(Subreddit.id == subreddit_key)

    origin_dict = u.model_dict(origin_sub)
    for key in list(origin_dict.keys()):
        # we remove the non-style keys from the dict
        if key.lower() not in KEYS_TO_COPY:
            origin_dict.pop(key, None)

    logger.debug('copying style of r/%s to r/%s...', origin_sub.name, subreddit.name)
    Subreddit.update(**origin_dict).where(Subreddit.id == subreddit.id).execute()

    text = '/r/{origin_sub} (channel: {origin_channel}) style applyed to /r/{dest_sub} (channel: {dest_channel})'.format(
        origin_sub=origin_sub.name,
        origin_channel=origin_sub.channel_title(),
        dest_sub=subreddit.name,
        dest_channel=subreddit.channel_title(),
    )
    update.message.reply_text(text, reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
@d.logconversation
def on_cancel(update: Update, _):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Okay, operation canceled', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


mainbot.add_handler(ConversationHandler(
    entry_points=[
        CommandHandler(command=['clonestylefrom'], callback=on_clonestylefrom_command)],
    states={
        Status.WAITING_ORIGIN_SUBREDDIT: [
            MessageHandler(Filters.text, callback=on_origin_subreddit_selected)
        ]
    },
    fallbacks=[
        CommandHandler(['cancel', 'done'], on_cancel)
    ]
))