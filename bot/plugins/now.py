import datetime
import logging
import re

import pytz
from telegram.ext import CommandHandler, CallbackContext

from bot import mainbot
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)

NOW_TEXT = """<b>UTC</b>: {utc_time}

{localized_times}

<b>UTC weekday</b>: {weekday}"""

DATETIME_FORMAT = '%d/%m/%Y, %H:%M'

TIMEZONES_MAP = dict(
    it=pytz.timezone('Europe/Rome'),
    ny=pytz.timezone('America/New_York'),
    la=pytz.timezone('America/Los_Angeles')
)


@d.restricted
@d.failwithmessage
def now_command(update, context: CallbackContext):
    logger.info('/now command')

    selected_hour = None
    if context.args:
        if not re.search(r'^\d+$', context.args[0]):
            update.message.reply_text('Argument must be a number')
            return

        selected_hour = int(context.args[0])
        if selected_hour > 23:
            update.message.reply_text('Argument must be <= 23')
            return

    now_utc = u.now()
    if selected_hour is not None:
        logger.info('replacing utc hour with %d', selected_hour)
        now_utc = now_utc.replace(hour=selected_hour)

    timezones_strings = list()
    for tz_key, pytz_timezone in TIMEZONES_MAP.items():
        time_string = u.localize_utc(now_utc, pytz_timezone).strftime(DATETIME_FORMAT)
        timezones_strings.append('<b>{}</b>: {}'.format(tz_key.upper(), time_string))

    weekday = datetime.datetime.today().weekday()
    update.message.reply_html(NOW_TEXT.format(
        utc_time=now_utc.strftime(DATETIME_FORMAT),
        localized_times='\n'.join(timezones_strings),
        weekday=weekday
    ))


mainbot.add_handler(CommandHandler(['now'], now_command))
