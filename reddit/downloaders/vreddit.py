import os
import re
import random
import subprocess

from reddit.downloaders import Downloader
from utilities import u
from config import config

if os.name == 'nt':  # windows: we expect ffmpeg to be in the main directory of the project
    FFMPEG_COMMAND = config.ffmpeg.cmd_path_windows + ' -i {video} -i {audio} -c:v copy -c:a aac -strict experimental {output}'
else:
    FFMPEG_COMMAND = config.ffmpeg.cmd_path + ' -i {video} -i {audio} -c:v copy -c:a aac -strict experimental {output}'


class VReddit(Downloader):
    def __init__(self, url, *args, **kwargs):
        Downloader.__init__(self, url, *args, **kwargs)
        self._file_path = os.path.join('downloads', '{}.mp4'.format(self._identifier))

        self._url_audio = re.sub(r'\/DASH_.*$', '/audio', self._url)
        self._size_audio = 0
        self._audio_path = os.path.join('downloads', '{}.mp3'.format(self._identifier))
        self._merged_path = self._file_path.replace('.mp4', '_merged.mp4')

    @property
    def audio_path(self):
        return self._audio_path

    def __repr__(self):
        return '<VReddit {} - {}>'.format(self._url, self._url_audio)

    def remove(self, keep_thumbnail=False):
        try:
            self._thumbnail_bo.close()
        except:
            pass

        try:
            os.remove(self._file_path)
            os.remove(self._audio_path)
            os.remove(self._merged_path)
            if not keep_thumbnail:
                os.remove(self._thumbnail_path)
        except FileNotFoundError:
            pass

    def download_audio(self):
        u.download_file_stream(self._url_audio, self._audio_path)

        # get the size if we weren't able to do that via headers
        if not self._size_audio:
            self._size_audio = os.path.getsize(self._audio_path)

        return self._audio_path

    def merge(self):
        cmd = FFMPEG_COMMAND.format(
            video=self._file_path,
            audio=self._audio_path,
            output=self._merged_path
        )

        devnull = open(os.devnull, 'w')

        subprocess.call(cmd, shell=True, stdout=devnull, stderr=devnull)

        return self._merged_path
    
    def download_and_merge(self):
        self.download()
        self.download_audio()
        return self.merge()
