import logging

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from database.models import Subreddit
from reddit import Sender
from reddit import reddit
from utilities import d
from config import config

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['try'], pass_args=True)
@d.restricted
@d.failwithmessage
def try_submission(bot, update, args):
    logger.info('/try command')

    """post = Post.get(Post.submission_id == args[0])
    if not post:
        update.message.reply_text('No submission "{}" in the database'.format(args[0]))
        return"""

    submission_id = args[0].strip()

    submission = reddit.submission(id=submission_id)

    subreddit = Subreddit.fetch(submission.subreddit)
    if not subreddit:
        update.message.reply_text('No subreddit "{}" in the database'.format(submission.subreddit))
        return

    sender = Sender(bot, subreddit, submission)
    sender.post(chat_id=update.message.chat.id)

    update.message.reply_text('Posted (r/{}, {})'.format(submission.subreddit, submission.title))
