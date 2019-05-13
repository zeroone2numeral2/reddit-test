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
    icon_url = reddit.get_icon(sub_name)
    if not icon_url:
        update.message.reply_text('Subreddit "{}" does\' exist or doesn\'t have an icon'.format(sub_name))
        return

    file_path = os.path.join('downloads', 'icon_{}.png'.format(sub_name))

    with urllib.request.urlopen(icon_url) as response, open(file_path, 'wb') as out_file:
        data = response.read()
        out_file.write(data)

    with open(file_path, 'rb') as f:
        update.message.reply_document(f)

    os.remove(file_path)
