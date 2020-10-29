import logging

from telegram.ext import CommandHandler

from bot import mainbot
from reddit import creds
from database.queries import reddit_request
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def creds_usage(update, context):
    logger.info('/credsusage command')

    totals = reddit_request.creds_usage(valid_clients=creds.client_names_list)

    text = 'Last two days:\n'
    for usage in totals:
        text += '\n<code>{account_name} + {client_name}</code>: {count}'.format(**usage)

    update.message.reply_html(text)


mainbot.add_handler(CommandHandler('credsusage', creds_usage))
