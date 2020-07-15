import logging

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext
from peewee import IntegrityError

from bot import mainbot
from database.models import Style
from utilities import d
from utilities import u

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def on_newstyle_command(update: Update, context: CallbackContext):
    logger.info('/newstyle command')

    if not context.args:
        update.message.reply_text('Please provide the style name')
        return

    style_name = u.to_ascii(context.args[0].lower())
    if not style_name:
        update.message.reply_text('Invalid name')
        return

    try:
        Style.create(
            name=style_name,
            created=u.now(),
            updated=u.now()
        )
    except IntegrityError:
        update.message.reply_html('The style <code>{}</code> already exists'.format(style_name))
        return

    update.message.reply_html('Style <code>{}</code> created'.format(style_name))


mainbot.add_handler(CommandHandler(['newstyle', 'createstyle'], on_newstyle_command))
