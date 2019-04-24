import logging

from telegram.ext import CommandHandler

from bot import Plugins
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['force'], pass_job_queue=True, pass_args=True)
@d.restricted
@d.failwithmessage
def force_job(bot, update, job_queue, args):
    logger.info('forcing job...')

    if len(args) < 1:
        update.message.reply_text('Pass the name of the job')
        return

    job_name = args[0]

    try:
        job = job_queue.get_jobs_by_name(job_name)[0]
    except IndexError:
        update.message.reply_text('No job named "{}"'.format(job_name))
        return

    update.message.reply_text('Running...')
    job.run(bot)

    update.message.reply_text('...done')
