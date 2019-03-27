import logging
import re
from pprint import pformat
import os

from telegram.ext import CommandHandler

from bot import Plugins
from utilities import u
from utilities import d
from config import config

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['getconfig'])
@d.restricted
@d.failwithmessage
def getconfig_command(bot, update):
    logger.info('/getconfig command')

    update.message.reply_html('<code>{}</code>'.format(pformat(config)))


@Plugins.add(CommandHandler, command=['getlog', 'log'], pass_args=True)
@d.restricted
@d.failwithmessage
def getlog_command(bot, update, args):
    logger.info('/getlog command')

    file_path = config.logging.filepath
    if args and re.search(r'^\d+$', args[0], re.I):
        log_file_num = args[0]
        file_path = file_path.replace('.log', '.log.{}'.format(log_file_num))

    with open(os.path.normpath(file_path), 'rb') as f:
        update.message.reply_document(f)


@Plugins.add(CommandHandler, command=['getdb', 'db'])
@d.restricted
@d.failwithmessage
def getdb_command(bot, update):
    logger.info('/getdb command')

    with open(os.path.normpath(config.sqlite.filename), 'rb') as f:
        update.message.reply_document(f)


@Plugins.add(CommandHandler, command=['utc'])
@d.restricted
@d.failwithmessage
def utc_command(bot, update):
    logger.info('/utc command')

    update.message.reply_text(u.now(string=True))


@Plugins.add(CommandHandler, command=['remdl'])
@d.restricted
@d.failwithmessage
def remdl_command(bot, update):
    logger.info('/remdl command')

    files = [f for f in os.listdir('downloads') if f != '.gitkeep']
    for file in files:
        file_path = os.path.join('downloads', file)
        u.remove_file_safe(file_path)

    update.message.reply_text('Removed {} files'.format(len(files)))

