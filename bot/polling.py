import logging

import database.database
from .updater import updater
from .pluginregistration import Plugins
from .jobregistration import Jobs

from config import config

logger = logging.getLogger(__name__)


def main():
    logger.info('started as @%s', updater.bot.username)

    plugins_count = Plugins.load(config.plugins.dir, config.plugins.manifest)
    Plugins.register()
    logger.info('loaded %d plugin%s', plugins_count, '' if plugins_count == 1 else 's')

    jobs_count = Jobs.load(config.jobs.dir, config.jobs.manifest)
    Jobs.register()
    logger.info('loaded %d job%s', jobs_count, '' if jobs_count == 1 else 's')

    updater.start_polling(clean=True)
    updater.idle()
