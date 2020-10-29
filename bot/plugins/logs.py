import logging
import re
import os

from telegram.ext import CommandHandler, CallbackContext

from bot import mainbot
from utilities import u
from utilities import d
from config import config

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def remffmpeglogs_command(update, _):
    logger.info('/remffmpeglogs command')

    dir_path = os.path.join('logs', 'ffmpeg')
    files = [f for f in os.listdir(dir_path) if f != '.gitkeep']
    for file in files:
        file_path = os.path.join(dir_path, file)
        u.remove_file_safe(file_path)

    update.message.reply_text('Removed {} log files'.format(len(files)))


@d.restricted
@d.failwithmessage
def remsubslogs_command(update, _):
    logger.info('/remsubslogs command')

    dir_path = os.path.join('logs', 'subreddits')
    files = [f for f in os.listdir(dir_path) if f != '.gitkeep']
    for file in files:
        file_path = os.path.join(dir_path, file)
        if os.path.isdir(file_path):
            # ignore directories
            continue

        u.remove_file_safe(file_path)

    update.message.reply_text('Removed {} log files'.format(len(files)))


mainbot.add_handler(CommandHandler(['remffmpeglogs'], remffmpeglogs_command))
mainbot.add_handler(CommandHandler(['remsubslogs'], remsubslogs_command))
