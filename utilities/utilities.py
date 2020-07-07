import json
import os
import re
from math import floor
import urllib.request as urllib
from mimetypes import guess_type

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

from database.models import Subreddit

from config import config

logger = logging.getLogger(__name__)

DEFAULT_TIME_FORMAT = '%d/%m/%Y %H:%M'
VALID_SUB_REGEX = r'(?:\/?r\/)?([\w-]{3,22})'
STRING_TO_MINUTES_REGEX = re.compile(r'(?:(?P<hours>\d+)\s*h)?\s*(?:(?P<minutes>\d+)\s*m?)?$', re.I)

tz_DEFAULT = pytz.timezone('Europe/Rome')


def html_escape(string):
    return escape(string)


def now(string=False, utc=True):
    """Return a datetime object or a string

    :param string: True -> returns current datetime as a string (default format), str -> use the passed string as format
    :param utc: UTC time
    :return: datetime/string
    """

    if utc:
        now = datetime.datetime.utcnow()
    else:
        now = datetime.datetime.now(tz_DEFAULT)

    if not string:
        return now
    elif string == True:
        return now.strftime(DEFAULT_TIME_FORMAT)
    elif isinstance(string, str):
        return now.strftime(string)
    else:
        return now


def localize_utc(utc_time, pytz_timezone):
    if not isinstance(pytz_timezone, DstTzInfo):
        raise ValueError('pytz_timezone must be of type pytz.timezone')

    # https://stackoverflow.com/questions/25264811/pytz-converting-utc-and-timezone-to-local-time
    return pytz.utc.localize(utc_time, is_dst=None).astimezone(pytz_timezone)


def dotted(number):
    return re.sub(r'(\d)(?=(\d{3})+(?!\d))', r'\1.', '{}'.format(number))


def model_dict(model_instance, plain_formatted_string=False):
    model_instance_dict = model_to_dict(model_instance)
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
    return int('100' + re.search(r'(\d+)\.\s.+', channel_id_str).group(1)) * -1


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


def elapsed_time_smart(seconds):
    elapsed_minutes = seconds / 60
    elapsed_hours = elapsed_minutes / 60
    elapsed_days = elapsed_hours / 24

    # "n hours ago" if hours > 0, else "n minutes ago"
    if elapsed_days >= 1:
        string = '{} day'.format(floor(elapsed_days))
        if elapsed_days >= 2:
            string += 's'
    elif elapsed_hours >= 1:
        string = '{} hour'.format(floor(elapsed_hours))
        if elapsed_hours >= 2:
            string += 's'
    else:
        string = '{} minute'.format(floor(elapsed_minutes))
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


def split_text(strings_list, join_by: str=False):
    avg_string_len = sum(map(len, strings_list)) / len(strings_list)
    list_items_per_message = int(MAX_MESSAGE_LENGTH / avg_string_len)

    for i in range(0, len(strings_list), list_items_per_message):
        if not join_by:
            yield strings_list[i:i + list_items_per_message]
        else:
            yield join_by.join(strings_list[i:i + list_items_per_message])


def media_size(message) -> [int, None]:
    # media.file_size is ok for pyrogram types too

    size = None
    if message.video:
        size = message.video.file_size
    elif message.document:
        size = message.document.file_size
    elif message.animation:
        size = message.animation.file_size
    elif message.audio:
        size = message.audio.file_size
    elif message.photo:
        size = message.photo[-1].file_size

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


def number_of_daily_posts(s: Subreddit, print_debug=False):
    n = 0

    if s.enabled:
        hours_of_reduced_frequency = 0
        if s.quiet_hours_demultiplier != 1.0:
            if s.quiet_hours_start > s.quiet_hours_end:
                hours_of_reduced_frequency += 24 - s.quiet_hours_start
                hours_of_reduced_frequency += s.quiet_hours_end + 1
            elif s.quiet_hours_start < s.quiet_hours_end:
                hours_of_reduced_frequency += s.quiet_hours_end - s.quiet_hours_start + 1

        hours_of_normal_frequency = 24 - hours_of_reduced_frequency

        minutes_of_normal_frequencies = hours_of_normal_frequency * 60
        minutes_of_reduced_frequency = hours_of_reduced_frequency * 60

        # number of messages during normal hours
        n_during_normal_hours = (minutes_of_normal_frequencies / s.max_frequency) * s.number_of_posts

        n_during_quiet_hours = 0
        if minutes_of_reduced_frequency:
            # number of messages during quiet hours
            if s.quiet_hours_demultiplier != 0.0:  # keep n_during_quiet_hours to 0 when quiet_hours_demultiplier is 0
                reduced_frequency = s.max_frequency * s.quiet_hours_demultiplier
                n_during_quiet_hours = (minutes_of_reduced_frequency / reduced_frequency) * s.number_of_posts

        n += n_during_normal_hours + n_during_quiet_hours

    if s.enabled_resume:
        n += s.number_of_posts

    n_rounded = round(n)

    if print_debug:
        print('hours_of_normal_frequency', hours_of_normal_frequency)
        print('minutes_of_normal_frequencies', minutes_of_normal_frequencies)
        print()
        print('hours_of_reduced_frequency', hours_of_reduced_frequency)
        print('minutes_of_reduced_frequency', minutes_of_reduced_frequency)
        print()
        print('n_during_normal_hours', n_during_normal_hours)
        print('n_during_quiet_hours', n_during_quiet_hours)
        print()
        print('n', n)
        print('n_rounded', n_rounded)

    return n_rounded
