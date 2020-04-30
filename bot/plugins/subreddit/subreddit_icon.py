import logging
import os

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from bot import mainbot
from bot.markups import Keyboard
from reddit import reddit
from utilities import d

logger = logging.getLogger(__name__)

SUBREDDIT_SELECT = 0


@d.restricted
@d.failwithmessage
def sub_icon(update: Update, context: CallbackContext):
    logger.info('/geticon command')

    if len(context.args) < 1:
        update.message.reply_text('Pass the subreddit name')
        return

    sub_name = context.args[0]
    file_path = reddit.get_icon(sub_name, download=True)
    if not file_path:
        update.message.reply_text('Subreddit "{}" does not have an icon'.format(sub_name))
        return

    with open(file_path, 'rb') as f:
        update.message.reply_document(f, caption='#icon_{}'.format(sub_name))

    os.remove(file_path)


@d.restricted
@d.failwithmessage
@d.pass_subreddit(answer=True)
def sub_set_icon(update: Update, context: CallbackContext, subreddit=None):
    logger.info('/setchannelicon command')

    file_path = reddit.get_icon(subreddit.name, download=True)
    if not file_path:
        update.message.reply_text('Subreddit "{}" does\' exist or doesn\'t have an icon'.format(subreddit.name),
                                  reply_markup=Keyboard.REMOVE)
        return

    with open(file_path, 'rb') as f:
        context.bot.set_chat_photo(subreddit.channel.channel_id, f)

    os.remove(file_path)

    update.message.reply_text('Icon updated')


mainbot.add_handler(CommandHandler(['geticon', 'icon'], sub_icon, pass_args=True))
mainbot.add_handler(CommandHandler(['setchannelicon'], sub_set_icon))
