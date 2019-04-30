import logging
import os

from telegram import Update
from telegram.ext import MessageHandler
from telegram.ext import Filters
from ptbplugins import Plugins

from database.models import Subreddit
from database.models import Channel
from database.models import Post
from reddit import Sender
from reddit import reddit
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(MessageHandler, filters=Filters.forwarded)
@d.restricted
@d.failwithmessage
def on_forwarded_post(bot, update: Update):
    logger.info('forwarded message')
    
    if not update.message.forward_from_chat:
        logger.info('the message is not forwarded from a channel')
        return
    
    channel_id = update.message.forward_from_chat.id
    message_id = update.message.forward_from_message_id
    
    channel = Channel.safe_get(channel_id)
    if not channel:
        update.message.reply_text('This channel is not in the database')
        return
    
    post = Post.get_post_by_message(channel, message_id)
    if not post:
        update.message.reply_text('Cannot find post (channel_id: {}, message_id: {})'.format(channel_id, message_id))
        return
    
    submission_id = post.submission_id
    
    submission = reddit.submission(id=submission_id)

    subreddit = Subreddit.fetch(submission.subreddit)
    if not subreddit:
        update.message.reply_text('No subreddit "{}" in the database'.format(submission.subreddit))
        return

    sender = Sender(bot, subreddit, submission)

    file_path = sender.write_temp_submission_dict()

    with open(file_path, 'rb') as f:
        update.message.reply_document(f)

    os.remove(file_path)
