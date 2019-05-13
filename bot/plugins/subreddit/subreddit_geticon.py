import logging
import os
import urllib.request

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from reddit import reddit
from utilities import d

logger = logging.getLogger(__name__)


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
        update.message.reply_text('Subreddit "{}" does\' exist or doesn\'t have an icon'.format(sub_name))
        return

    with open(file_path, 'rb') as f:
        update.message.reply_document(f)

    os.remove(file_path)
