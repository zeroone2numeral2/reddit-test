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
from reddit import reddit

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def on_placeholders_command(update, context):
    logger.info('/placeholders command')

    sender = None
    subreddit = Subreddit.select().get()
    slogger.set_subreddit(subreddit)
    for submission in reddit.iter_submissions(subreddit.name, limit=1):
        sender = Sender(context.bot, subreddit, submission, slogger)
        break
    
    placeholders = list()
    for key, val in sender.submission_dict.items():
        placeholders.append('{} ({})'.format(key.strip(), str(type(val))))
    
    text = '\n'.join(placeholders)
    try:
        update.message.reply_text(text)
        raise TelegramError
    except (TelegramError, BadRequest):
        file_path = 'downloads/template.temp.txt'
        
        with open(file_path, 'w+') as f:
            f.write(text)
        
        with open(file_path, 'rb') as f:
            update.message.reply_document(f)
        
        os.remove(file_path)


mainbot.add_handler(CommandHandler(['placeholders', 'ph'], on_placeholders_command))
