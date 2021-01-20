import logging
import os

from telegram.ext import CommandHandler
from telegram.error import TelegramError
from telegram.error import BadRequest

from bot import mainbot
from bot.logging import slogger
from utilities import d
from database.models import Subreddit
from reddit import Sender
from reddit import Reddit, creds

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def on_placeholders_command(update, context):
    logger.info('/placeholders command')

    account = creds.default_account
    reddit = Reddit(**account.creds_dict(), **account.default_client.creds_dict())

    sender = None
    subreddit = Subreddit.select().where(Subreddit.channel.is_null(False)).get()
    slogger.set_subreddit(subreddit)
    for position, submission in reddit.iter_submissions(subreddit.name, limit=1):
        sender = Sender(context.bot, subreddit, submission, slogger)
        break
    
    placeholders = list()
    for key, val in sender.submission_dict.items():
        if not isinstance(val, (str, int, float)) or isinstance(val, bool):
            # we need to check for "bool" because "bool" is a subclass of "int",
            # so isinstance(val, int) returns True for bool
            continue

        val_type = str(type(val))
        placeholders.append('{}'.format(key.strip()))

    text = "\n".join(placeholders)
    text_html = "<code>" + text + "</code>"
    try:
        update.message.reply_html(text_html)
    except (TelegramError, BadRequest):
        file_path = 'downloads/template.temp.txt'
        
        with open(file_path, 'w+') as f:
            f.write(text)
        
        with open(file_path, 'rb') as f:
            update.message.reply_document(f)
        
        os.remove(file_path)


mainbot.add_handler(CommandHandler(['placeholders', 'ph'], on_placeholders_command))
