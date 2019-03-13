import logging
import re
from html import escape
import datetime
import pytz

from playhouse.shortcuts import model_to_dict

logger = logging.getLogger(__name__)

DEFAULT_TIME_FORMAT = '%d/%m/%Y %H:%M'

timezone = pytz.timezone('Europe/Rome')


def html_escape(string):
    return escape(string)


def now(string=False, timezone_aware=False, utc=True):
    """Return a datetime object or a string

    :param string: True -> returns current datetime as a string (default format), str -> use the passed string as format
    :param timezone_aware: 'Europe/Rome' time
    :param utc: UTC time. Has the priority over 'timezone_aware'
    :return: datetime/string
    """

    if utc:
        now = datetime.datetime.utcnow()
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


def dotted(number):
    return re.sub('(\d)(?=(\d{3})+(?!\d))', r'\1.', '{}'.format(number))


def model_dict(model_instance, plain_formatted_string=False):
    model_instance_dict = model_to_dict(model_instance)
    if not plain_formatted_string:
        return model_instance
    else:
        text = '\n'.join('{}: {}'.format(k, v) for k, v in model_instance_dict.items())
        text = '<code>{}</code>'.format(escape(text))
        return text
