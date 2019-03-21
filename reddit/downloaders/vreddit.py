import os
import random

from reddit.downloaders import Downloader


class VReddit(Downloader):
    def __init__(self, url, identifier=random.randint(1, 10000)):
        Downloader.__init__(self, url, identifier)
        self._file_path = os.path.join('downloads', '{}.mp4'.format(identifier))

    def __repr__(self):
        return '<VReddit {} ({})>'.format(self._url, self._size_readable)
