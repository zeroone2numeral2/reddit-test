import json
import logging
from pprint import pformat
import os

from telegram.ext import CommandHandler

from bot import mainbot
from database.models import Subreddit
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

    url = context.args[0]

    update.message.reply_video(url)


@d.restricted
@d.failwithmessage
def json_command(update, _):
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


mainbot.add_handler(CommandHandler(['getconfig'], getconfig_command))
mainbot.add_handler(CommandHandler(['getdb', 'db'], getdb_command))
mainbot.add_handler(CommandHandler(['remdl'], remdl_command))
mainbot.add_handler(CommandHandler(['sendv'], sendv_command))
mainbot.add_handler(CommandHandler(['json'], json_command))
