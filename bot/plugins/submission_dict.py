import logging
import os
from pprint import pformat

from telegram.ext import CommandHandler
from telegram import MAX_MESSAGE_LENGTH
from ptbplugins import Plugins

from utilities import d
from database.models import Subreddit
from reddit import Sender
from reddit import reddit

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['sdict'], pass_args=True)
@d.restricted
@d.failwithmessage
@d.knownsubreddit
def subs_list(bot, update, args):
    logger.info('/sdict command')
    
    sender = None
    subreddit = Subreddit.fetch(args[0])
    for submission in reddit.iter_submissions(subreddit.name, limit=1):
        sender = Sender(bot, subreddit, submission)
        break
    
    text = pformat(sender.submission_dict)
    if len(text) < MAX_MESSAGE_LENGTH:
        update.message.reply_html('<code>{}</code>'.format(text))
    else:
        file_path = sender.write_temp_submission_dict()
        
        with open(file_path, 'rb') as f:
            update.message.reply_document(f)
        
        os.remove(file_path)
