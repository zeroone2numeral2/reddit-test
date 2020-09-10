import logging

from telegram import Update
from telegram.ext import CommandHandler

from bot import mainbot
from database.queries import settings
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def on_lock_status(update: Update, _):
    logger.info('/lockstatus command')

    jobs_locked = settings.jobs_locked()

    if jobs_locked:
        text = '<b>Jobs are locked right now</b>. Use /unlock to make them resume'
    else:
        text = 'Jobs are not locked'

    update.message.reply_html(text)


@d.restricted
@d.failwithmessage
def on_lock(update: Update, _):
    logger.info('/lock command')

    settings.lock_jobs()
    update.message.reply_html('Jobs are now locked (some tasks need to complete anyway)')


@d.restricted
@d.failwithmessage
def on_unlock(update: Update, _):
    logger.info('/unlock command')

    settings.unlock_jobs()
    update.message.reply_html('Jobs are now unlocked')


mainbot.add_handler(CommandHandler(['lockstatus'], on_lock_status))
mainbot.add_handler(CommandHandler(['lock'], on_lock))
mainbot.add_handler(CommandHandler(['unlock'], on_unlock))
