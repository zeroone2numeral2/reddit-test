import logging

from telegram import Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler

from bot import mainbot
from reddit import creds
from database.queries import reddit_request
from database.queries import settings
from utilities import d
from config import reddit

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def creds_stats(update, context):
    logger.info('/credstats command')

    totals = reddit_request.creds_usage(valid_clients=creds.client_names_list)

    total = 0
    text = 'Last {} hours:\n'.format(reddit.general.stress_threshold_hours)
    for usage in totals:
        total += usage['count']
        text += '\n<code>{account_name} + {client_name}</code>: {count}'.format(**usage)

    actual_total = total * 2  # submission + comments
    text += '\n\n<b>Total</b>: {}*2: {} ({}/hour,{}/minute)'.format(
        total,
        actual_total,
        int(actual_total / reddit.general.stress_threshold_hours),
        int(actual_total / reddit.general.stress_threshold_hours / 60)
    )

    update.message.reply_html(text)


@d.restricted
@d.failwithmessage
def on_usage_mode(update: Update, context: CallbackContext):
    logger.info('/credsusagemode command')

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


mainbot.add_handler(CommandHandler('credstats', creds_stats))
mainbot.add_handler(CommandHandler(['credsusagemode'], on_usage_mode))
