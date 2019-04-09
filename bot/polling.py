import logging

import database.database  # we need it to initialize the package as soon as possible
from .updater import updater
from .updater import dispatcher
from .updater import job_queue
from .pluginregistration import Plugins
from .jobregistration import Jobs

from config import config

logger = logging.getLogger(__name__)


def main():
    logger.info('started as @%s', updater.bot.username)

    Plugins.hook(updater.dispatcher)
    plugins_count = Plugins.load(config.plugins.dir, config.plugins.manifest)
    Plugins.register()
    logger.info('loaded %d plugin%s', plugins_count, '' if plugins_count == 1 else 's')

    Jobs.hook(dispatcher, job_queue)
    jobs_count = Jobs.load(config.jobs.dir, config.jobs.manifest)
    Jobs.register()
    logger.info('loaded %d job%s', jobs_count, '' if jobs_count == 1 else 's')

    updater.start_polling(clean=True)
    updater.idle()
