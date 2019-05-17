import datetime
import logging
from collections import KeysView

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from utilities import u
from utilities import d

logger = logging.getLogger(__name__)

NOW_TEXT = """\
<b>UTC</b>: {utc_time}
<b>Localized ({tz_key})</b>: {localized_time}

Weekday: {weekday}\
"""
DATETIME_FORMAT = '%d/%m/%Y, %H:%M'


@Plugins.add(CommandHandler, command=['now'], pass_args=True)
@d.restricted
@d.failwithmessage
def now_command(_, update, args):
    logger.info('/now command')

    timezone = 'it'
    if args:
        timezone = args[0].lower()

    now_utc = u.now()
    now_tz = u.localize_utc(now_utc, timezone)
    if isinstance(now_tz, KeysView):
        # u.localize_utc returned a list: the timezone we passed is invalid
        update.message.reply_text('Valid timezone keys: {}'.format(', '.join(now_tz)))
        return

    weekday = datetime.datetime.today().weekday()
    update.message.reply_html(NOW_TEXT.format(
        utc_time=now_utc.strftime(DATETIME_FORMAT),
        localized_time=now_tz.strftime(DATETIME_FORMAT),
        weekday=weekday,
        tz_key=timezone
    ))


@Plugins.add(CommandHandler, command=['tz'])
@d.restricted
@d.failwithmessage
def tz_command(_, update):
    logger.info('/tz command')

    timezones_list = u.localize_utc(_, '')
    update.message.reply_text('Timezone keys: {}'.format(', '.join(timezones_list)))
