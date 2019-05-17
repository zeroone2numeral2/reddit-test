import logging
import re
import os

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from utilities import u
from utilities import d
from config import config

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['loglines'])
@d.restricted
@d.failwithmessage
def loglines_command(_, update):
    logger.info('/loglines command')

    dir_path = os.path.dirname(config.logging.filepath)

    lines_list = list()
    dir_files = [f for f in os.listdir(dir_path)][:50]
    for file in dir_files:
        file_path = os.path.join(dir_path, file)
        if not re.search(r'.+\.log(?:\.\d+)?', file_path, re.I):
            continue

        with open(file_path) as f:
            lines_list.append('{} - {}'.format(f.readline()[:25], str(file)))

    text = '<code>{}</code>'.format('\n'.join(sorted(lines_list)))

    update.message.reply_html(text)


@Plugins.add(CommandHandler, command=['remffmpeglogs'])
@d.restricted
@d.failwithmessage
def remffmpeglogs_command(_, update):
    logger.info('/remffmpeglogs command')

    dir_path = os.path.join('logs', 'ffmpeg')
    files = [f for f in os.listdir(dir_path) if f != '.gitkeep']
    for file in files:
        file_path = os.path.join(dir_path, file)
        u.remove_file_safe(file_path)

    update.message.reply_text('Removed {} log files'.format(len(files)))


@Plugins.add(CommandHandler, command=['getlog', 'log'], pass_args=True)
@d.restricted
@d.failwithmessage
def getlog_command(_, update, args):
    logger.info('/getlog command')

    file_path = config.logging.filepath
    if args and re.search(r'^\d+$', args[0], re.I):
        log_file_num = args[0]
        file_path = file_path.replace('.log', '.log.{}'.format(log_file_num))

    with open(os.path.normpath(file_path), 'rb') as f:
        update.message.reply_document(f)
