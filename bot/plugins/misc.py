import json
import logging
from pprint import pformat
import os

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from database.models import Subreddit
from utilities import u
from utilities import d
from config import config

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['getconfig'])
@d.restricted
@d.failwithmessage
def getconfig_command(_, update):
    logger.info('/getconfig command')

    update.message.reply_html('<code>{}</code>'.format(pformat(config)))


@Plugins.add(CommandHandler, command=['getdb', 'db'])
@d.restricted
@d.failwithmessage
def getdb_command(_, update):
    logger.info('/getdb command')

    with open(os.path.normpath(config.sqlite.filename), 'rb') as f:
        update.message.reply_document(f)


@Plugins.add(CommandHandler, command=['remdl'])
@d.restricted
@d.failwithmessage
def remdl_command(_, update):
    logger.info('/remdl command')

    files = [f for f in os.listdir('downloads') if f != '.gitkeep']
    for file in files:
        file_path = os.path.join('downloads', file)
        u.remove_file_safe(file_path)

    update.message.reply_text('Removed {} files'.format(len(files)))


@Plugins.add(CommandHandler, command=['jobs'])
@d.restricted
@d.failwithmessage
def jobs_command(_, update):
    logger.info('/jobs command')

    subs = Subreddit.subreddits_with_jobs()

    if not subs:
        update.message.reply_text('No subs')
        return

    subs_strings = list()
    for sub in subs:
        jobs = list()
        if sub[1]:
            jobs.append('post')
        if sub[2]:
            jobs.append('resume')

        subs_strings.append('r/{} ({})'.format(sub[0], ', '.join(jobs)))

    update.message.reply_text('\n'.join(subs_strings))


@Plugins.add(CommandHandler, command=['json'])
@d.restricted
@d.failwithmessage
def json_command(_, update):
    logger.info('/json command')

    data = list()

    subreddits = (
        Subreddit.select()
    )
    for subreddit in subreddits:
        data.append(u.model_dict(subreddit))

    # json.sumps() doesn't work because it can't serialize datetime values
    # skipkeys just skip the "keys", not the "values"
    text = json.dumps(data, skipkeys=True, indent=4)
    file = u.FileWriter('downloads/export.tmp.json', text, write=True)

    with open(file.file_path, 'rb') as f:
        update.message.reply_document(f)

    file.remove()
