import logging
import re
from pprint import pformat
import os

from telegram.ext import CommandHandler

from bot import Plugins
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


@Plugins.add(CommandHandler, command=['getlog', 'log'], pass_args=True)
@d.restricted
@d.failwithmessage
def getlog_command(_, update, args):
    logger.info('/getlog command')

    file_path = config.logging.filepath
    if args and re.search(r'^\d+$', args[0], re.I):
        log_file_num = args[0]
        file_path = file_path.replace('.log', '.log.{}'.format(log_file_num))

    with open(os.path.normpath(file_path), 'rb') as f:
        update.message.reply_document(f)


@Plugins.add(CommandHandler, command=['getdb', 'db'])
@d.restricted
@d.failwithmessage
def getdb_command(_, update):
    logger.info('/getdb command')

    with open(os.path.normpath(config.sqlite.filename), 'rb') as f:
        update.message.reply_document(f)


@Plugins.add(CommandHandler, command=['utc'])
@d.restricted
@d.failwithmessage
def utc_command(_, update):
    logger.info('/utc command')

    update.message.reply_text(u.now(string=True))


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


@Plugins.add(CommandHandler, command=['remffmpeglogs'])
@d.restricted
@d.failwithmessage
def remffmpeglogs_command(_, update):
    logger.info('/remffmpeglogs command')

    dir_path = os.path.join('logs', 'ffmpeg')
    files = [f for f in os.listdir(dir_path) if f != '.gitkeep']
    for file in files:
        file_path = os.path.join(dir_path, file)
        u.remove_file_safe(file_path)

    update.message.reply_text('Removed {} log files'.format(len(files)))


@Plugins.add(CommandHandler, command=['jobs'])
@d.restricted
@d.failwithmessage
def remdl_command(_, update):
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
    

@Plugins.add(CommandHandler, command=['loglines'])
@d.restricted
@d.failwithmessage
def loglines_command(_, update):
    logger.info('/loglines command')
    
    dir_path = os.path.dirname(config.logging.filepath)
    
    lines_list = list()
    dir_files = [f for f in os.listdir(dir_path)][:50]
    for file in dir_files:
        file_path = os.path.join(dir_path, file)
        if not re.search(r'.+\.log(?:\.\d+)?', file_path, re.I):
            continue
        
        with open(file_path) as f:
            lines_list.append('{} - {}'.format(f.readline()[:25], str(file)))
    
    text = '<code>{}</code>'.format('\n'.join(lines_list))
    
    update.message.reply_html(text)
