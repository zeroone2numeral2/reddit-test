import logging

from telegram.ext import CommandHandler

from bot import Plugins
from database.models import Post
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

    post = Post.get(Post.submission_id == args[0])
    if not post:
        update.message.reply_text('No submission "{}"'.format(args[0]))
        return

    submission_id = args[0].strip()

    submission = reddit.submission(id=submission_id)
    sender = Sender(bot, post.subreddit, submission)
    sender.post(chat_id=update.message.chat.id)

    update.message.reply_text('Posted (r/{}, {})'.format(submission.subreddit,submission.title))
