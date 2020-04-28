import logging

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from bot import mainbot
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def force_job(update: Update, context: CallbackContext):
    logger.info('forcing job...')

    if len(context.args) < 1:
        update.message.reply_text('Pass the name of the job')
        return

    job_name = context.args[0]

    try:
        job = context.job_queue.get_jobs_by_name(job_name)[0]
    except IndexError:
        update.message.reply_text('No job named "{}"'.format(job_name))
        return

    update.message.reply_text('Running...')
    job.run(context)

    update.message.reply_text('...done')


mainbot.add_handler(CommandHandler(['force'], force_job, pass_job_queue=True, pass_args=True))
