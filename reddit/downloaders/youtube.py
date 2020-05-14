import logging
import os
import re
from copy import deepcopy
from pprint import pformat

import youtube_dl

from .image import Image
from utilities import u
from const import MaxSize

logger = logging.getLogger('ytdl')


class YouTubeFileTooBig(Exception):
    pass


class YouTubeTooLong(Exception):
    pass


class YouTubeIsStreaming(Exception):
    pass


class DloadOpts(object):
    AUDIO = {
        'format': 'bestaudio/best',  # https://github.com/rg3/youtube-dl/blob/master/README.md#format-selection
        'outtmpl': u'downloads/%(title)s_%(id)s.%(ext)s',
        'restrictfilenames': True,  # https://github.com/rg3/youtube-dl/blob/master/README.md#filesystem-options
        # 'phantomjs_location': '/root/ytdl-bot/phantomjs',  # https://github.com/rg3/youtube-dl/pull/17527
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            # 'preferredquality': '320',
        }]
    }

    VIDEO = {
        'format': 'best/bestvideo',
        'outtmpl': u'downloads/%(title)s_%(id)s.%(ext)s',
        'restrictfilenames': True,
        # 'phantomjs_location': '/root/ytdl-bot/phantomjs',
        'recodevideo': 'mp4',  # https://github.com/rg3/youtube-dl/blob/c3bcd206eb031de30179c88ac7acd806a477ceae/youtube_dl/__init__.py#L262
    }


class YouTube:
    def __init__(self, url, max_size=MaxSize.BOT_API, max_duration=0):
        self.url = url
        self.info_dict = dict()
        self.actual_url = None  # actual download url
        self.webpage_url = None  # url of the video webpage
        self.file_path = None
        self.file_name = None
        self.thumb: [None, Image] = None
        self.is_streaming = False
        self.title = None
        self.size = 0
        self.size_readable = '0 bytes'
        self.max_size = max_size
        self.duration = None
        self.max_duration = max_duration
        self.skip_download = False  # this is True when 'skip_download' is passed to self.download()
        self.ascii_title = ''
        self.id = None  # video id
        self.last_dl_tick = 0
        self.height = None
        self.width = None
        self._thumbnail_bo = None

    def progress_hook(self, d):
        # print(d)
        if d['status'] == 'finished':
            logger.info('finished')
            self.file_path = os.path.normpath(d['filename'])

            head, tail = os.path.split(self.file_path)
            self.file_name = tail
        elif d['status'] == 'downloading':
            downloaded_bytes = d.get('downloaded_bytes', 0) or 0
            total_bytes = d.get('total_bytes', 0) or 0
            logger.info('progress hook - total bytes: %d, downloaded bytes: %d', total_bytes, downloaded_bytes)

    def _process_info_dict(self):
        # logger.debug('video info dict: %s', pformat(self.info_dict))

        self.id = self.info_dict.get('id', None)
        self.actual_url = self.info_dict.get('url', '')
        self.webpage_url = self.info_dict.get('webpage_url', '')
        self.duration = int(self.info_dict.get('duration', 0))
        self.thumb_url = self.info_dict.get('thumbnail', None)
        self.is_streaming = self.info_dict.get('is_live', False)
        self.title = self.info_dict.get('title', 'no title')
        self.ascii_title = re.sub(r'\W+', '', self.title or '')

        self.height = self.info_dict.get('height', None)
        self.width = self.info_dict.get('width', None)

        if self.is_streaming:
            logger.info('video %s is streaming: skipping download', self.id)
        else:
            logger.info('video %s is not streaming', self.id)

    def check_size(self, raise_exception=True):
        if self.size > self.max_size:
            if raise_exception:
                raise YouTubeFileTooBig('file size is too big for Telegram: {}'.format(self.size_readable))
            else:
                return False

        return True

    def download(self):
        logger.info('starting download of %s', self.url)

        opts = deepcopy(DloadOpts.VIDEO)

        opts['progress_hooks'] = [self.progress_hook]  # noqa

        with youtube_dl.YoutubeDL(opts) as ytdl:
            self.info_dict = ytdl.extract_info(self.url, download=False)
            self._process_info_dict()

            if self.is_streaming:
                logger.info('video is streaming: skipping')
                raise YouTubeTooLong('duration too long: {} seconds'.format(self.duration))

            if self.max_duration and self.duration > self.max_duration:
                logger.info('video is too long (%d vs %d): skipping', self.duration, self.max_duration)
                raise YouTubeTooLong('this video is a streaming')

            ytdl.download([self.url])

            logger.info('download finished, file_name after download: %s', self.file_name)

        if self.thumb_url:
            logger.info('thumb url: %s', self.thumb_url)
            self.thumb = Image(self.thumb_url, use_tempfile=True)
            self.thumb.download()
            # logger.info('thumb path: %s', self.thumb_path)

        self.size = os.stat(self.file_path).st_size
        self.size_readable = u.human_readable_size(self.size)
        logger.info('file size: %d bytes (%s)', self.size, self.size_readable)

        self.check_size(raise_exception=True)

        return True

    def remove(self, keep_thumbnail=False):
        logger.info('deleting song file and thumbnail')

        try:
            if self.file_path:
                os.remove(self.file_path)
            if self.thumb:
                self.thumb.close()
        except Exception as e:
            logger.info('exception while deleting the file(s): %s', str(e))