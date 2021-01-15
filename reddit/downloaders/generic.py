import os
import random

import requests

from const import MaxSize
from utilities import u


class FileTooBig(Exception):
    pass


class Downloader:
    def __init__(self, url, thumbnail_url='', identifier=random.randint(1, 10000), max_size=MaxSize.BOT_API, logger=None):
        self._url = url
        self._identifier = identifier
        self._file_path = os.path.join('downloads', '{}.mp4'.format(self._identifier))
        self._size = 0
        self._thumbnail_url = thumbnail_url
        self._thumbnail_path = ''
        self._thumbnail_bo = None
        self._max_size = max_size
        self.subreddit_logger = logger

        if self._thumbnail_url == 'nsfw':
            self._thumbnail_url = 'https://t3.ftcdn.net/jpg/01/77/29/28/240_F_177292812_asUGEDiieLfHjKx9DxTBI50vsS9iZwi0.jpg '

        headers = requests.head(url).headers
        if 'content-length' in headers:
            self._size = int(headers.get('content-length', 0))

    @property
    def url(self):
        return self._url

    @property
    def file_path(self):
        return self._file_path

    @property
    def size_readable(self):
        # it might change during the processing of the files (eg. see vreddit video/audio merge),
        # so we have to generate the string every time
        return u.human_readable_size(self._size)

    @property
    def size(self):
        return self._size

    @property
    def thumbnail_path(self):
        return self._thumbnail_path

    @thumbnail_path.setter
    def thumbnail_path(self, path):
        self._thumbnail_path = path

    @property
    def thumbnail_url(self):
        return self._thumbnail_url

    def __repr__(self):
        return '<Downloaded content {} ({})>'.format(self._url, self.size_readable)

    def check_size(self, raise_exception=True):
        if self._size > self._max_size:
            if raise_exception:
                raise FileTooBig('file size is too big for Telegram: {}'.format(self.size_readable))
            else:
                return False

        return True

    def download(self):
        self.check_size()

        u.download_file_stream(self._url, self._file_path)

        # get the size if we weren't able to do that via headers
        if not self._size:
            self._size = os.path.getsize(self._file_path)

            self.check_size()  # check the size again and raise an exception if necessary

        return self._file_path

    def download_thumbnail(self, resize=True):
        if not self._thumbnail_url:
            return None

        self._thumbnail_path = u.download_file(
            self._thumbnail_url,
            file_path=os.path.join('downloads', 'thumb_{}.jpg'.format(self._identifier))
        )
        if resize:
            self._thumbnail_path = u.resize_thumbnail(self._thumbnail_path)

        return True

    def get_thumbnail_bo(self):
        self._thumbnail_bo = open(self._thumbnail_path, 'rb')

        return self._thumbnail_bo

    def remove(self, keep_thumbnail=False):
        # noinspection PyBroadException
        try:
            self._thumbnail_bo.close()
        except Exception:
            pass

        try:
            os.remove(self._file_path)
            if not keep_thumbnail:
                os.remove(self._thumbnail_path)
        except FileNotFoundError:
            pass
