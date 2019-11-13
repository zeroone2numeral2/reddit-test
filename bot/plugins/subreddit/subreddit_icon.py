import logging
import os

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from bot.markups import Keyboard
from reddit import reddit
from utilities import d

logger = logging.getLogger(__name__)

SUBREDDIT_SELECT = 0


@Plugins.add(CommandHandler, command=['geticon', 'icon'], pass_args=True)
@d.restricted
@d.failwithmessage
def sub_icon(_, update, args):
    logger.info('/geticon command')

    if len(args) < 1:
        update.message.reply_text('Pass the subreddit name')
        return

    sub_name = args[0]
    file_path = reddit.get_icon(sub_name, download=True)
    if not file_path:
        update.message.reply_text('Subreddit "{}" does not have an icon'.format(sub_name))
        return

    with open(file_path, 'rb') as f:
        update.message.reply_document(f, caption='#icon_{}'.format(sub_name))

    os.remove(file_path)


@Plugins.add(CommandHandler, command=['setchannelicon'])
@d.restricted
@d.failwithmessage
@d.pass_subreddit(answer=True)
def sub_seticon(bot, update, subreddit=None):
    logger.info('/setchannelicon command')

    file_path = reddit.get_icon(subreddit.name, download=True)
    if not file_path:
        update.message.reply_text('Subreddit "{}" does\' exist or doesn\'t have an icon'.format(subreddit.name),
                                  reply_markup=Keyboard.REMOVE)
        return

    with open(file_path, 'rb') as f:
        bot.set_chat_photo(subreddit.channel.channel_id, f)

    os.remove(file_path)

    update.message.reply_text('Icon updated')
