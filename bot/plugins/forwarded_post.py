import logging
import os

from telegram import Update
from telegram.ext import MessageHandler
from telegram.ext import CallbackQueryHandler
from telegram.ext import Filters

from bot import mainbot
from bot.markups import InlineKeyboard
from database.models import Subreddit
from database.models import Channel
from database.models import Post
from reddit import Sender
from reddit import reddit
from utilities import d

logger = logging.getLogger(__name__)


@d.restricted
@d.failwithmessage
def on_forwarded_post(update: Update, context):
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

    sender = Sender(context.bot, subreddit, submission)

    file_path = sender.write_temp_submission_dict()

    with open(file_path, 'rb') as f:
        update.message.reply_document(f)

    os.remove(file_path)

    markup = InlineKeyboard.vote(submission_id)
    update.message.reply_text('You can upvote/downvote this submission', reply_markup=markup)


@d.restricted
@d.failwithmessage
def up_down_button(update: Update, _, groups):
    logger.info('up/down inline button, groups: %s', groups)

    vote = groups[0]
    submission_id = groups[1]

    submission = reddit.submission(id=submission_id)

    # voting cannot be done by bots
    # see https://praw.readthedocs.io/en/latest/code_overview/models/submission.html#praw.models.Submission.downvote

    try:
        if vote == 'upvote':
            submission.upvote()
        elif vote == 'downvote':
            submission.downvote()
    except Exception as e:
        update.callback_query.answer('Error while voting: {}'.format(str(e)), show_alert=True)
        return

    update.callback_query.answer('Submission {}d'.format(vote))

    markup = InlineKeyboard.vote(submission_id, vote)
    update.callback_query.edit_message_reply_markup(markup)


mainbot.add_handler(MessageHandler(on_forwarded_post, Filters.forwarded))
mainbot.add_handler(CallbackQueryHandler(up_down_button, pattern=r'(\w+):(.+)', pass_groups=True))
