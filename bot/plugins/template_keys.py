import logging

from telegram.ext import CommandHandler

from bot import Plugins
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['placeholders', 'ph'])
@d.restricted
@d.failwithmessage
def subs_list(bot, update):
    logger.info('/placeholders command')
    
    try:
        with open('template_keys.txt', 'r') as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        update.message.reply_text('template_keys.txt not found')
        return
    
    placeholders = ['<code>{' + line.strip() + '}</code>' for line in lines]
    update.message.reply_html('\n'.join(placeholders))
