import logging

from telegram.ext import CommandHandler

from bot import Plugins
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['force'], pass_job_queue=True)
@d.restricted
@d.failwithmessage
def force_job(bot, update, job_queue):
    logger.info('forcing job...')

    job = job_queue.get_jobs_by_name('posts_job')[0]

    update.message.reply_text('Running...')
    job.run(bot)

    update.message.reply_text('...done')
