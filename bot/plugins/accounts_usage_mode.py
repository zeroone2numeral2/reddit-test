import logging

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from bot import mainbot
from database.queries import settings
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def on_usage_mode(update: Update, context: CallbackContext):
    logger.info('/usagemode command')

    if context.args:
        value = int(context.args[0])
        settings.change_accounts_usage_mode(value)
        update.message.reply_text('Setting changed')
    else:
        value = settings.get_accounts_usage_mode()

    values_map = {
        None: 'based on reddit.toml',
        0: 'based on reddit.toml',
        1: 'default account + its least used client',
        2: 'least used account + its least used client',
        3: 'least used client + its account'
    }

    text = 'Current value ({}): {}\n\nAccepted values: '.format(value, values_map[value])
    values_desc = list()
    for value, desc in values_map.items():
        if value is None:
            continue

        values_desc.append('{} {}'.format(value, desc))

    text += ', '.join(values_desc)
    update.message.reply_html(text)


mainbot.add_handler(CommandHandler(['usagemode'], on_usage_mode))
