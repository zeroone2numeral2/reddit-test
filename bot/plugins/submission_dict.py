import logging
import os
from pprint import pformat

from telegram.ext import CommandHandler
from telegram import MAX_MESSAGE_LENGTH

from bot import mainbot
from utilities import d
from database.models import Subreddit
from database.models import Channel
from reddit import Sender
from reddit import reddit

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
# @d.knownsubreddit
def on_sdict_command(update, context):
    logger.info('/sdict command')

    submission_id = context.args[0].strip()
    submission = reddit.submission(id=submission_id)

    # pick a random channel to pass to Sender
    tmp_channel = Channel.select().order_by(Channel.channel_id.desc()).get()

    # try to get the real subreddit if we have it saved in the db
    sub_id = submission.subreddit.name
    if Subreddit.get_safe(subreddit_id=sub_id):
        tmp_subreddit = Subreddit.get_safe(subreddit_id=sub_id)
    else:
        tmp_subreddit = Subreddit(
            subreddit_id=submission.subreddit.id,
            channel=tmp_channel,
            name=str(submission.subreddit)
        )
        update.message.reply_text('"{}" not in the db, using fake subreddit object...'.format(sub_id))

    tmp_subreddit.logger = logger
    sender = Sender(context.bot, tmp_subreddit, submission)
    
    text = pformat(sender.submission_dict)
    if len(text) < MAX_MESSAGE_LENGTH:
        update.message.reply_html('<code>{}</code>'.format(text))
    else:
        file_path = sender.write_temp_submission_dict()
        
        with open(file_path, 'rb') as f:
            update.message.reply_document(f)
        
        os.remove(file_path)


mainbot.add_handler(CommandHandler('sdict', on_sdict_command))
