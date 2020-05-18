import logging

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from bot import mainbot
from database.models import Job
from utilities import d
from utilities import u
from config import config

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def durations_command(update: Update, context: CallbackContext):
    logger.info('/duration command')

    if context.args:
        job_name = context.args[0]
    else:
        job_name = None

    durations = Job.durations(top=100, job_name=job_name)
    if not durations:
        update.message.reply_text('No row in the database')
        return

    strings_list = list()
    for duration in durations:
        strings_list.append('{0}: {2}/{3} ({start})'.format(*duration, start=duration[1].strftime('%d/%m/%Y %H:%M:%S')))

    update.message.reply_html('<code>$job_name: $seconds/$messages ($start)\n{}</code>'.format('\n'.join(strings_list)))


@d.restricted
@d.failwithmessage
def lastjob_command(update: Update, _):
    logger.info('/lastjob command')

    text = ''
    now = u.now()
    for job_name, job_info in config.jobs.items():
        job_duration = Job.last_job(job_name=job_name)
        if job_duration:
            text += '\n\n<b>{}</b>:\n• {}\n• {} ago\n• every {} minutes'.format(
                job_name,
                job_duration.end.strftime('%d/%m/%Y %H:%M:%S'),
                u.pretty_seconds((now - job_duration.end).total_seconds()),
                job_info['interval']
            )

    if not text:
        update.message.reply_text('No row in the database')
        return

    update.message.reply_html(text)


mainbot.add_handler(CommandHandler(['duration', 'durations'], durations_command))
mainbot.add_handler(CommandHandler(['lastjob'], lastjob_command))
