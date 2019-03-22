import os
import random

import requests

from utilities import u
from const import MAX_SIZE


class FileTooBig(Exception):
    pass


class Downloader:
    def __init__(self, url, identifier=random.randint(1, 10000)):
        self._url = url
        self._file_path = '{}.mp4'.format(identifier)
        self._size = 0
        self._size_readable = '0 b'

        headers = requests.head(url).headers
        if 'Content-Type' in headers:
            self._size = int(headers.get('content-length', 0))
            self._size_readable = u.human_readable_size(self._size)

    @property
    def url(self):
        return self._url

    @property
    def file_path(self):
        return self._file_path

    @property
    def size_readable(self):
        return self._size_readable

    def __repr__(self):
        return '<Downloaded content {} ({})>'.format(self._url, self._size_readable)

    def check_size(self, raise_exception=True):
        if self._size > MAX_SIZE:
            if raise_exception:
                raise FileTooBig('file size is too big for Telegram: {}'.format(self._size_readable))
            else:
                return False

        return True

    def download(self):
        self.check_size()

        u.download_file_stream(self._url, self._file_path)

        # get the size if we weren't able to do that via headers
        if not self._size:
            self._size = os.path.getsize(self._file_path)
            self._size_readable = u.human_readable_size(self._size)

            self.check_size()  # check the size again and raise an exception if necessary

        return self._file_path

    def remove(self):
        try:
            os.remove(self._file_path)
        except FileNotFoundError:
            pass
