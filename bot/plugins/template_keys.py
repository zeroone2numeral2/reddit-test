import logging

from telegram.ext import CommandHandler

from bot import Plugins
from utilities import d
from utilities import u
from database.models import Subreddit
from reddit import Sender
from reddit import reddit

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['placeholders', 'ph'])
@d.restricted
@d.failwithmessage
def subs_list(bot, update):
    logger.info('/placeholders command')

    sender = None
    subreddit = Subreddit.select().get()
    for submission in reddit.iter_submissions(subreddit.name, limit=1):
        sender = Sender(bot, subreddit, submission)
        break
    
    placeholders = list()
    for key, val in sender.submission_dict.items():
        placeholders.append('{} ({})'.format(key.strip(), u.html_escape(str(type(val)))))
        
    update.message.reply_html('\n'.join(placeholders))
