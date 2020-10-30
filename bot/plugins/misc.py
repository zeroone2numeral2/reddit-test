import json
import logging
from pprint import pformat
import os

from telegram.ext import CommandHandler

from bot import mainbot
from database.models import Subreddit
from database.models import Post
from database.models import PostResume
from database.models import Job
from database.models import SubredditJob
from database.models import RedditRequest
from database.queries.channels import get_channels
from utilities import u
from utilities import d
from config import config

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def getconfig_command(update, _):
    logger.info('/getconfig command')

    update.message.reply_html('<code>{}</code>'.format(pformat(config)))


@d.restricted
@d.failwithmessage
def getdb_command(update, _):
    logger.info('/getdb command')

    with open(os.path.normpath(config.sqlite.filename), 'rb') as f:
        update.message.reply_document(f)


@d.restricted
@d.failwithmessage
def remdl_command(update, _):
    logger.info('/remdl command')

    files = [f for f in os.listdir('downloads') if f != '.gitkeep']
    for file in files:
        file_path = os.path.join('downloads', file)
        u.remove_file_safe(file_path)

    update.message.reply_text('Removed {} files'.format(len(files)))


@d.restricted
@d.failwithmessage
def sendv_command(update, context):
    logger.info('/sendv command')
    get_channels()


@d.restricted
@d.failwithmessage
def json_command(update, _):
    logger.info('/json command')

    data = list()
    for subreddit in Subreddit.select():
        data.append(subreddit.to_dict())

    # json.sumps() doesn't work because it can't serialize datetime values
    # skipkeys just skip the "keys", not the "values"
    text = json.dumps(data, skipkeys=True, indent=2)
    file = u.FileWriter('downloads/export.tmp.json', text, write=True)

    with open(file.file_path, 'rb') as f:
        update.message.reply_document(f)

    file.remove()


@d.restricted
@d.failwithmessage
def cleandb_command(update, _):
    logger.info('/cleandb command')

    days = 31

    deleted_records = dict(
        post=Post.delete_old(days),
        post_resume=PostResume.delete_old(days),
        job=Job.delete_old(days),
        subreddit_job=SubredditJob.delete_old(days),
        reddit_request=RedditRequest.delete_old(days),
    )

    import sqlite3
    conn = sqlite3.connect(config.sqlite.filename, isolation_level=None)
    conn.execute("VACUUM")
    conn.close()

    lines = ['{}: {}'.format(k, v) for k, v in deleted_records.items()]
    update.message.reply_html('Days: {}\n<code>{}</code>'.format(days, '\n'.join(lines)))


mainbot.add_handler(CommandHandler(['getconfig'], getconfig_command))
mainbot.add_handler(CommandHandler(['getdb', 'db'], getdb_command))
mainbot.add_handler(CommandHandler(['remdl'], remdl_command))
mainbot.add_handler(CommandHandler(['sendv'], sendv_command))
mainbot.add_handler(CommandHandler(['json'], json_command))
mainbot.add_handler(CommandHandler(['cleandb'], cleandb_command))
