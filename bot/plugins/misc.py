import logging
from pprint import pformat
import os

from telegram.ext import CommandHandler

from bot import Plugins
from utilities import d
from config import config

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['getconfig'])
@d.restricted
@d.failwithmessage
def getconfig_command(bot, update):
    logger.info('/getconfig command')

    update.message.reply_html('<code>{}</code>'.format(pformat(config)))


@Plugins.add(CommandHandler, command=['getlog', 'log'])
@d.restricted
@d.failwithmessage
def getlog_command(bot, update):
    logger.info('/getlog command')

    with open(os.path.normpath(config.logging.filepath), 'rb') as f:
        update.message.reply_document(f)
