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
def subconfig_on_clonestylefrom_command(update: Update, context: CallbackContext):
    logger.info('/clonestylefrom command, args: %s', str(context.args))

    # we consider the second argument as a filter for the destination subreddit selection keyboard
    name_filter = context.args[0] if context.args else None

    subreddits = Subreddit.get_list(name_filter=name_filter)
    if not subreddits:
        update.message.reply_text('Cannot find any subreddit (filter: {})'.format(name_filter))
        return Status.WAITING_SUBREDDIT_CONFIG_ACTION

    reply_markup = Keyboard.from_list(['{}. /r/{} ({})'.format(s.id, s.name, s.channel.title) for s in subreddits])

    update.message.reply_text('Select the subreddit to copy the style from, or /cancel:', reply_markup=reply_markup)

    return Status.WAITING_ORIGIN_SUBREDDIT


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_subreddit_2
def subconfig_on_clonestyle_origin_subreddit_selected(update: Update, _, subreddit: Subreddit):
    logger.info('/clonestylefrom command: origin subreddit selected (%s)', update.message.text)

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

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation
def subconfig_on_clonestyle_selected_subreddit_wrong(update: Update, _):
    logger.info('unexpected message while selecting a subreddit')
    update.message.reply_text('Select a subreddit, or /cancel')

    return Status.CLONESTYLE_WAITING_ORIGIN_SUBREDDIT
