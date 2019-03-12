import logging
from html import escape
import datetime
import pytz

logger = logging.getLogger(__name__)

DEFAULT_TIME_FORMAT = '%d/%m/%Y %H:%M'

timezone = pytz.timezone('Europe/Rome')


def html_escape(string):
    return escape(string)


def now(string=False, timezone_aware=True, utc=False):
    """Return a datetime object or a string

    :param string: True -> returns current datetime as a string (default format), str -> use the passed string as format
    :param timezone_aware: 'Europe/Rome' time
    :param utc: UTC time. Has the priority over 'timezone_aware'
    :return: datetime/string
    """

    if utc:
        now = datetime.datetime.now(datetime.timezone.utc)
    elif timezone_aware:
        now = timezone.localize(datetime.datetime.now())
    else:
        now = datetime.datetime.now()

    if not string:
        return now
    elif string == True:
        return now.strftime(DEFAULT_TIME_FORMAT)
    elif isinstance(string, str):
        return now.strftime(string)
    else:
        return now
