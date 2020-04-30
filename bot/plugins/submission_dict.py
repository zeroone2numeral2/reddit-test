import logging
import os
from pprint import pformat

from telegram.ext import CommandHandler
from telegram import MAX_MESSAGE_LENGTH

from bot import mainbot
from utilities import d
from database.models import Subreddit
from reddit import Sender
from reddit import reddit

logger = logging.getLogger(__name__)


@d.restricted
@d.failwithmessage
@d.knownsubreddit
def on_sdict_command(update, context):
    logger.info('/sdict command')
    
    sender = None
    subreddit = Subreddit.fetch(context.args[0])
    for submission in reddit.iter_submissions(subreddit.name, limit=1):
        sender = Sender(context.bot, subreddit, submission)
        break
    
    text = pformat(sender.submission_dict)
    if len(text) < MAX_MESSAGE_LENGTH:
        update.message.reply_html('<code>{}</code>'.format(text))
    else:
        file_path = sender.write_temp_submission_dict()
        
        with open(file_path, 'rb') as f:
            update.message.reply_document(f)
        
        os.remove(file_path)


mainbot.add_handler(CommandHandler('sdict', on_sdict_command))
