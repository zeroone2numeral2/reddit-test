import logging

from telegram import Update
from telegram.ext import CommandHandler

from bot import mainbot
from const import DEFAULT_TEMPLATES
from utilities import u
from utilities import d

logger = logging.getLogger('handler')

SUBREDDIT_SELECT = 0


@d.restricted
@d.failwithmessage
def get_templates(update: Update, _):
    logger.info('/templates command')

    strings = list()
    for i, template in enumerate(DEFAULT_TEMPLATES):
        strings.append('Template #{}:\n<code>{}</code>'.format(i + 1, u.escape(template)))

    for text in u.split_text(strings, join_by='\n\n'):
        update.message.reply_html(text)


mainbot.add_handler(CommandHandler(['templates'], get_templates))
