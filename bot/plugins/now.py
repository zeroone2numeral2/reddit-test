import datetime
import logging
from collections import KeysView

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from utilities import u
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['now'], pass_args=True)
@d.restricted
@d.failwithmessage
def now_command(_, update, args):
    logger.info('/now command')

    timezone = None
    if args:
        timezone = args[0]

    now = u.now()
    if timezone:
        now = u.localize_utc(now, timezone.lower())
        if isinstance(now, KeysView):
            # u.localize_utc returned a list: the timezone we passed is invalid
            update.message.reply_text('Valid timezone keys: {}'.format(', '.join(now)))
            return

    weekday = datetime.datetime.today().weekday()
    update.message.reply_text('{}\nWeekday: {}\nTimezone: {}'.format(
        now.strftime('%d/%m/%Y %H:%M'),
        weekday,
        timezone or 'none'
    ))


@Plugins.add(CommandHandler, command=['tz'])
@d.restricted
@d.failwithmessage
def tz_command(_, update):
    logger.info('/tz command')

    timezones_list = u.localize_utc(_, '')
    update.message.reply_text('Timezone keys: {}'.format(', '.join(timezones_list)))
