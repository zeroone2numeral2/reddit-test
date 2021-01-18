import logging
import os

from telegram.ext import CommandHandler

from bot import mainbot
from database.models import Subreddit, Style
from database.models import Channel
from reddit import Sender
from reddit import Reddit, creds
from utilities import u
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def try_submission(update, context):
    logger.info('/try command')

    submission_id = context.args[0].strip()

    account = creds.default_account
    reddit = Reddit(**account.creds_dict(), **account.default_client.creds_dict())
    submission = reddit.submission(id=submission_id)
    if not hasattr(submission, 'current_position'):
        submission.current_position = 1

    # pick a random channel to pass to Sender
    tmp_channel = Channel.select().order_by(Channel.channel_id.desc()).get()

    # try to get the real subreddit if we have it saved in the db
    sub_id = submission.subreddit.name
    if u.get_subreddit_from_userdata(context.user_data):
        tmp_subreddit = u.get_subreddit_from_userdata(context.user_data)
    elif Subreddit.get_safe(subreddit_id=sub_id):
        tmp_subreddit = Subreddit.get_safe(subreddit_id=sub_id)
    else:
        tmp_subreddit = Subreddit(
            subreddit_id=submission.subreddit.id,
            channel=tmp_channel,
            name=str(submission.subreddit),
            style=Style.get_default()
        )
        update.message.reply_text('"{}" not in the db, using fake subreddit object...'.format(sub_id))

    tmp_subreddit.logger = logger
    sender = Sender(context.bot, tmp_subreddit, submission)
    
    file_path = sender.write_temp_submission_dict()

    with open(file_path, 'rb') as f:
        update.message.reply_document(f)

    os.remove(file_path)
    
    sender.post(chat_id=update.message.chat.id)

    update.message.reply_text('Posted (r/{}, {})'.format(submission.subreddit, submission.title))


mainbot.add_handler(CommandHandler('try', try_submission))
