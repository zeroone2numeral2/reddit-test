import logging

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from database.models import Job
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['duration', 'durations'])
@d.restricted
@d.failwithmessage
def durations_command(_, update):
    logger.info('/duration command')

    durations = Job.durations(top=100)
    if not durations:
        update.message.reply_text('No row in the database')
        return

    strings_list = list()
    for duration in durations:
        strings_list.append('{0}: {2} ({start})'.format(*duration, start=duration[1].strftime('%d/%m/%Y %H:%M:%S')))

    update.message.reply_html('<code>{}</code>'.format('\n'.join(strings_list)))
