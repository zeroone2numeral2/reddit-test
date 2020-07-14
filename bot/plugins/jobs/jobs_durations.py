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

    durations = Job.durations(top=50, job_name=job_name)
    if not durations:
        update.message.reply_text('No row in the database')
        return

    strings_list = list()
    for duration in durations:
        uploaded = u.human_readable_size(duration[4] or 0)
        strings_list.append('{0}: {2}/{3}, {uploaded} ({start})'.format(
            *duration,
            uploaded=uploaded,
            start=duration[1].strftime('%d/%m/%Y %H:%M:%S'))
        )

    update.message.reply_html('<code>$job_name: $seconds/$messages, $uploaded_data ($start)\n{}</code>'.format('\n'.join(strings_list)))


@d.restricted
@d.failwithmessage
def lastjob_command(update: Update, _):
    logger.info('/lastjob command')

    text = ''
    for job_name, job_info in config.jobs.items():
        job_duration = Job.last_job(job_name=job_name)

        if not job_duration:
            continue

        text += '\n\n<b>{name}</b>:\n• ended: {ended}\n• lasted: {elapsed}\n• every {interval} minutes'.format(
            name=job_name,
            ended=job_duration.end_dt.strftime('%d/%m/%Y %H:%M:%S') if job_duration.end else 'running',
            elapsed=u.pretty_seconds(job_duration.duration) if job_duration.duration else 'running',
            interval=job_info['interval']
        )

    if not text:
        update.message.reply_text('No row in the database')
        return

    update.message.reply_html(text)


mainbot.add_handler(CommandHandler(['duration', 'durations'], durations_command))
mainbot.add_handler(CommandHandler(['lastjob'], lastjob_command))
