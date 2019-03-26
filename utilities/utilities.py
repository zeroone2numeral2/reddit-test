import os
import re
import pytz
import math
import json
import logging
import logging.config
import datetime
from html import escape

import requests
from PIL import Image

from playhouse.shortcuts import model_to_dict

logger = logging.getLogger(__name__)

DEFAULT_TIME_FORMAT = '%d/%m/%Y %H:%M'
VALID_SUB_REGEX = r'(?:\/?r\/)?([\w-]{3,22})'
STRING_TO_MINUTES_REGEX = re.compile(r'(?:(?P<hours>\d+)\s*h)?\s*(?:(?P<minutes>\d+)\s*m?)?$', re.I)

timezone = pytz.timezone('Europe/Rome')


def load_logging_config(file_path, logfile):
    with open(file_path, 'r') as f:
        logging_config = json.load(f)
    logging_config['handlers']['file']['filename'] = logfile
    logging.config.dictConfig(logging_config)


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
    return re.sub(r'(\d)(?=(\d{3})+(?!\d))', r'\1.', '{}'.format(number))


def model_dict(model_instance, plain_formatted_string=False):
    model_instance_dict = model_to_dict(model_instance)
    if not plain_formatted_string:
        return model_instance
    else:
        text = '\n'.join('<code>{}</code>: {}'.format(escape(k), escape(str(v))) for k, v in model_instance_dict.items())
        return text


def normalize_sub_name(name):
    match = re.search(VALID_SUB_REGEX, name, re.I)
    if not match:
        return None
    else:
        return match.group(1)


def expand_channel_id(channel_id_str):
    return int('100' + re.search(r'(\d+)\.\s.+', channel_id_str).group(1)) * -1


def pretty_minutes(n):
    if n < 60:
        return '{}m'.format(n)

    hours = int(n / 60)
    minutes = n % 60

    string = '{}h'.format(hours)

    if minutes != 0:
        minutes_str = str(minutes) if minutes > 10 else '0' + str(minutes)
        string += '{}m'.format(minutes_str)

    return string


def elapsed_time_smart(seconds):
    elapsed_minutes = seconds / 60
    elapsed_hours = elapsed_minutes / 60

    # "n hours ago" if hours > 0, else "n minutes ago"
    if elapsed_hours >= 1:
        string = '{} hour'.format(int(elapsed_hours))
        if elapsed_hours >= 2:
            string += 's'
    else:
        string = '{} minute'.format(int(elapsed_minutes))
        if elapsed_minutes >= 2:
            string += 's'

    return string


def human_readable_size(size, precision=2):
    suffixes = ['b', 'kb', 'mb', 'gb', 'tb']
    suffix_index = 0
    while size > 1024 and suffix_index < 4:
        suffix_index += 1  # increment the index of the suffix
        size = size / 1024.0  # apply the division

    return '%.*f %s' % (precision, size, suffixes[suffix_index])


def download_file_stream(url, file_path=None, chunk_size=1024):
    # https://stackoverflow.com/a/16696317

    r = requests.get(url, stream=True)

    with open(file_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=chunk_size):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                # f.flush() commented by recommendation from J.F.Sebastian

    return file_path


def resize_thumbnail(image_path):
    if not image_path:
        raise FileNotFoundError

    image = Image.open(image_path)

    if image.size[0] < 91 and image.size[1] < 91:
        sizes = image.size
    else:
        i = 0 if image.size[0] > image.size[1] else 1  # index of the largest dimension
        new = [None, None]
        new[i] = 90
        rateo = 90 / image.size[i]
        new[1 if i == 0 else 0] = int(math.floor(image.size[1 if i == 0 else 0] * round(rateo, 4)))

        sizes = tuple(new)

    image = image.resize(sizes, Image.ANTIALIAS)
    image.save(image_path)

    return image_path


def remove_file_safe(file_path):
    try:
        os.remove(file_path)
    except:
        pass


def is_valid_sub_name(name):
    return bool(re.search('(?:/?r/)?[\w-]{3,20}', name, re.I))


def string_to_minutes(string):
    match = STRING_TO_MINUTES_REGEX.search(string)
    if match:
        hours, minutes = match.group('hours', 'minutes')
        sum_minutes = 0
        if hours:
            sum_minutes += int(hours) * 60
        if minutes:
            sum_minutes += int(minutes)

        return sum_minutes if sum_minutes > 0 else None
