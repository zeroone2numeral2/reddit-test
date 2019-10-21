import logging
import os
from pprint import pformat

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from database.models import Subreddit
from database.models import Channel
from reddit import Sender
from reddit import reddit
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['try'], pass_args=True)
@d.restricted
@d.failwithmessage
def try_submission(bot, update, args):
    logger.info('/try command')

    submission_id = args[0].strip()

    submission = reddit.submission(id=submission_id)

    # pick a random channel to pass to Sender
    tmp_channel = Channel.select().order_by(Channel.channel_id.desc()).get()

    tmp_subreddit = Subreddit(
        subreddit_id=submission.subreddit.id,
        channel=tmp_channel,
        name=str(submission.subreddit)
    )

    # try to get the real subreddit if we have it saved in the db
    if Subreddit.fetch(submission.subreddit.name):
        tmp_subreddit = Subreddit.fetch(submission.subreddit.name)

    sender = Sender(bot, tmp_subreddit, submission)
    
    file_path = sender.write_temp_submission_dict()

    with open(file_path, 'rb') as f:
        update.message.reply_document(f)

    os.remove(file_path)
    
    sender.post(chat_id=update.message.chat.id)

    update.message.reply_text('Posted (r/{}, {})'.format(submission.subreddit, submission.title))
