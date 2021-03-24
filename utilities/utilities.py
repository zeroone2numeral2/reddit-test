import json
import os
import re
from math import floor
import urllib.request as urllib
from mimetypes import guess_type
from typing import Tuple, List

import pytz
from pytz.tzinfo import DstTzInfo
import math
import logging.config
import datetime
from html import escape
from collections import OrderedDict

import requests
from PIL import Image

from playhouse.shortcuts import model_to_dict
from telegram import MAX_MESSAGE_LENGTH

from config import config

logger = logging.getLogger(__name__)

DEFAULT_TIME_FORMAT = '%d/%m/%Y %H:%M'
VALID_SUB_REGEX = r'(?:\/?r\/)?([\w-]{3,22})'
STRING_TO_MINUTES_REGEX = re.compile(r'(?:(?P<hours>\d+)\s*h)?\s*(?:(?P<minutes>\d+)\s*m?)?$', re.I)

tz_DEFAULT = pytz.timezone('Europe/Rome')


def html_escape(string):
    return escape(string)


def now(string=False, utc=True, tz=None):
    """Return a datetime object or a string

    :param string: True -> returns current datetime as a string (default format), str -> use the passed string as format
    :param utc: UTC time
    :return: datetime/string
    """

    if utc and tz:
        raise ValueError("pass either tc or a timezone")

    if not tz or tz is True:
        tz = tz_DEFAULT

    if utc:
        now = datetime.datetime.utcnow()
    else:
        now = datetime.datetime.now(tz)

    if not string:
        return now
    elif string is True:
        return now.strftime(DEFAULT_TIME_FORMAT)
    elif isinstance(string, str):
        return now.strftime(string)
    else:
        return now


def print_dt(dt_obj):
    print(dt_obj.strftime('%d/%m/%Y %H:%M:%S') + " " + str(dt_obj.tzinfo))


def localize_utc(utc_time, pytz_timezone):
    if not isinstance(pytz_timezone, DstTzInfo):
        raise ValueError('pytz_timezone must be of type pytz.timezone')

    # https://stackoverflow.com/questions/25264811/pytz-converting-utc-and-timezone-to-local-time
    return pytz.utc.localize(utc_time, is_dst=None).astimezone(pytz_timezone)


def replace_timezone(dt_object, pytz_timezone):
    if not isinstance(pytz_timezone, DstTzInfo):
        raise ValueError('pytz_timezone must be of type pytz.timezone')

    return dt_object.replace(tzinfo=pytz_timezone)


def dotted(number):
    return re.sub(r'(\d)(?=(\d{3})+(?!\d))', r'\1.', '{}'.format(number))


def model_dict(model_instance, plain_formatted_string=False, ignore_keys: [list, tuple] = None):
    model_instance_dict = model_to_dict(model_instance)
    if ignore_keys:
        for key in ignore_keys:
            model_instance_dict.pop(key, None)

    model_instance_dict = OrderedDict(sorted(model_instance_dict.items()))
    if not plain_formatted_string:
        return model_instance_dict
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
    return int('100' + re.search(r'^(\d+).*', channel_id_str).group(1)) * -1


def pretty_minutes(n_minutes):
    if n_minutes < 60:
        return '{}m'.format(n_minutes)

    hours = int(n_minutes / 60)
    minutes = n_minutes % 60

    string = '{}h'.format(hours)

    if minutes != 0:
        minutes_str = str(minutes) if minutes > 10 else '0' + str(minutes)
        string += '{}m'.format(minutes_str)

    return string


def pretty_seconds(n_seconds):
    if n_seconds < 0:
        n_seconds = n_seconds * -1

    if n_seconds < 60:
        return '{}s'.format(n_seconds)

    hours = int(n_seconds / 3600)
    minutes = int(n_seconds / 60) % 60
    seconds = int(n_seconds % 60)

    string = ''
    if hours:
        string += '{}h '.format(hours)

    if minutes != 0 or (hours and seconds):
        string += '{}m '.format(minutes)

    if seconds or (minutes == 0 and hours == 0):
        string += '{}s'.format(seconds)

    return string


def elapsed_time_smart(seconds, compact=False):
    if compact:
        days_string = 'd'
        hours_string = 'h'
        minutes_string = 'm'
    else:
        days_string = ' day'
        hours_string = ' hour'
        minutes_string = ' minute'

    elapsed_minutes = seconds / 60
    elapsed_hours = elapsed_minutes / 60
    elapsed_days = elapsed_hours / 24

    # "n hours ago" if hours > 0, else "n minutes ago"
    if elapsed_days >= 1:
        string = '{}{}'.format(floor(elapsed_days), days_string)
        if elapsed_days >= 2 and not compact:
            string += 's'
    elif elapsed_hours >= 1:
        string = '{}{}'.format(floor(elapsed_hours), hours_string)
        if elapsed_hours >= 2 and not compact:
            string += 's'
    else:
        string = '{}{}'.format(floor(elapsed_minutes), minutes_string)
        if elapsed_minutes >= 2 and not compact:
            string += 's'

    return string


def elapsed_smart_compact(seconds):
    if seconds < 1:
        return '{}s'.format(seconds)

    string = ''

    days = seconds // (3600 * 24)
    seconds %= 3600 * 24
    if days:
        string += '{}d'.format(int(days))

    hours = seconds // 3600
    seconds %= 3600
    if hours:
        string += '{}h'.format(int(hours))

    minutes = seconds // 60
    seconds %= 60
    if minutes:
        string += '{}m'.format(int(minutes))

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


def download_file(url, file_path):
    try:
        dloaded_file = urllib.urlopen(url)
        with open(file_path, 'wb') as output:
            output.write(dloaded_file.read())
    except Exception as e:
        logger.info('execption while downloading thumb: %s', str(e), exc_info=True)
        return None

    return file_path


def resize_thumbnail(image_path):
    if not image_path:
        raise FileNotFoundError

    image = Image.open(image_path)

    if image.size[0] < 321 and image.size[1] < 321:
        sizes = image.size
    else:
        i = 0 if image.size[0] > image.size[1] else 1  # index of the largest dimension
        new = [None, None]
        new[i] = 320
        rateo = 320 / image.size[i]
        new[1 if i == 0 else 0] = int(math.floor(image.size[1 if i == 0 else 0] * round(rateo, 4)))

        sizes = tuple(new)

    image = image.resize(sizes, Image.ANTIALIAS)
    image = image.convert('RGB')  # avoid RGBA (png) images to raise an exception because they cannot be saved as JPG

    image.save(image_path)

    return image_path


def remove_file_safe(file_path):
    # noinspection PyBroadException
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


def guess_mimetype(file_path):
    result = guess_type(file_path, strict=True)
    
    return result[0]


def to_ascii(string, replace_spaces=False, lowercase=False):
    # return string.encode("ascii", errors="ignore").decode()
    result_string = re.sub(r'[^\w]', '', string)

    if replace_spaces:
        result_string = result_string.replace(' ', '_')

    if lowercase:
        result_string = result_string.lower()

    return result_string


def string_to_python_val(value):
    if value in ('true', 'True'):
        logger.info('value is True')
        value = True
    elif value in ('false', 'False'):
        logger.info('value is False')
        value = False
    elif value in ('none', 'None'):
        logger.info('value is None')
        value = None
    elif re.search(r'^\d+$', value, re.I):
        logger.info('value is int')
        value = int(value)
    elif re.search(r'^\d+\.\d+$', value, re.I):
        logger.info('value is float')
        value = float(value)

    return value


class FileWriter:
    def __init__(self, file_path, text, write=False):
        self.file_path = file_path
        self.text = text

        if write:
            self.write()

    def write(self):
        with open(self.file_path, 'w+') as f:
            f.write(self.text)

    def remove(self):
        os.remove(self.file_path)


def print_submission(submission):
    attrs = [a for a in dir(submission) if not a.startswith('_')]
    max_key_len = len(max(attrs, key=len))

    base_string = '{:.<%d} > {}' % max_key_len
    for attr in attrs:
        try:
            string = base_string.format(attr, getattr(submission, attr))
            print(string)
        except Exception as e:
            string = base_string.format(attr, 'EXCEPTION: ' + str(e))
            print(string)


def message_link(message):
    if message.chat.username:
        return 'https://t.me/{}/{}'.format(message.chat.username, message.message_id)
    else:
        return 'https://t.me/c/{}/{}'.format(str(message.chat.id)[3:], message.message_id)


def split_text(strings_list, join_by: str = False):
    total_len = sum(map(len, strings_list))
    avg_string_len = total_len / len(strings_list)

    list_items_per_message = int(MAX_MESSAGE_LENGTH / avg_string_len)

    for i in range(0, len(strings_list), list_items_per_message):
        if not join_by:
            yield strings_list[i:i + list_items_per_message]
        else:
            yield join_by.join(strings_list[i:i + list_items_per_message])


def split_text_2(strings_list, join_by: str = '\n'):
    text_chunk = ''
    for i in range(0, len(strings_list)):
        new_text_chunk = '{}{}{}'.format(text_chunk, join_by, strings_list[i])

        if len(new_text_chunk) < MAX_MESSAGE_LENGTH:
            # if the new chunk is shorter, approve it and continue with the next item
            text_chunk = new_text_chunk
            continue
        else:
            # if the new chunk is longer, return the previous text chunk and use the new item as the beginning of
            # another text chunk
            yield text_chunk
            text_chunk = strings_list[i]


def media_size(messages) -> [int, None]:
    # media.file_size is ok for pyrogram types too
    if not isinstance(messages, list):
        messages = [messages]

    size = 0
    for message in messages:
        if message.video:
            size += message.video.file_size
        elif message.document:
            size += message.document.file_size
        elif message.animation:
            size += message.animation.file_size
        elif message.audio:
            size += message.audio.file_size
        elif message.photo:
            size += message.photo[-1].file_size

    return size


def channel_invite_link(channel, return_on_no_link=None, hyperlink_html: [str, None] = None):
    if channel.username:
        channel_url = 'https://t.me/' + channel.username
    elif channel.invite_link:
        channel_url = channel.invite_link
    else:
        return return_on_no_link

    if not hyperlink_html:
        return channel_url
    else:
        return '<a href="{}">{}</a>'.format(channel_url, html_escape(hyperlink_html))


def get_subreddit_from_userdata(user_data: dict):
    if not user_data.get('data', None):
        return
    else:
        return user_data['data'].get('subreddit', None)


def proper_round(num, dec=0):
    num = str(num)[:str(num).index('.') + dec + 2]

    if num[-1] >= '5':
        return float(num[:-2 - (not dec)] + str(int(num[-2 - (not dec)]) + 1))

    return float(num[:-1])


def text_messages_from_list(strings_list: list):
    total_len = sum(map(len, strings_list))
    avg_len = total_len / len(strings_list)
    elements_per_msg = int(MAX_MESSAGE_LENGTH / avg_len)

    for i in range(0, len(strings_list), elements_per_msg):
        yield strings_list[i:i + elements_per_msg]


def remove_duplicates(origin_list, sort=True):
    result_list = []
    [result_list.append(x) for x in origin_list if x not in result_list]

    if sort:
        result_list.sort()

    return result_list


def pretty_time(total_minutes, sep=', ', round_by=10):
    """Pretty string representation of minutes

    :param total_minutes: time in minutes
    :param sep: string that separates hours and minutes (if both present)
    :param round_by: round minutes to the highest multiple of 'round_by' possible
    :return: string
    """

    hours = int(total_minutes / 60)
    minutes = total_minutes - (hours * 60)

    if (minutes % round_by) != 0:
        minutes = minutes + (round_by - (minutes % round_by))
        if minutes == 60:
            minutes = 0
            hours += 1

    string = ''
    if hours > 0:
        if hours > 1:
            string += '{} hours'.format(hours)
        else:
            string += 'one hour'

    if minutes > 0:
        if hours > 0:
            string += sep

        string += '{} minutes'.format(minutes)

    return string


def username_to_link(username, html=False):
    url = "https://reddit.com/user/{}".format(username)

    if not html:
        return url

    return '<a href="{}">/u/{}</a>'.format(url, username)


def username_to_link_but_cool(username):
    url = "https://reddit.com/user/{}".format(username)

    return '<a href="{}">/u/</a><code>{}</code>'.format(url, username)


def id_match_from_list(provided_id: [int, str], ids_list: list) -> Tuple[bool, List[str]]:
    """returns two values: first value is a bool that will be true if there's a perfect match, the second one is a list
    of matches"""
    provided_id = str(provided_id)
    ids_list = [str(_id) for _id in ids_list]

    # check for perfect match first
    for _id in ids_list:
        if provided_id == _id:
            return True, [_id]

    matches = []
    for _id in ids_list:
        if _id.startswith(provided_id):
            matches.append(_id)

    return False, matches
