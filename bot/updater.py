from telegram.ext import Updater

from config import config

updater = Updater(token=config.telegram.token, workers=config.telegram.workers, use_context=True)
dispatcher = updater.dispatcher
job_queue = updater.job_queue
