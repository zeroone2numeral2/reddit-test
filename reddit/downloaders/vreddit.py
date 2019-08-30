import os
import re
import logging
import subprocess
import urllib.request
import urllib.error

from reddit.downloaders import Downloader
from utilities import u
from config import config


TIME_FORMAT = '%d/%m/%Y %H:%M:%S'
FFMPEG_COMMAND_ARGS = ' -i {video} -i {audio} -c:v copy -c:a aac -strict experimental {output} -y'

if os.name == 'nt':  # windows: we expect ffmpeg to be in the main directory of the project
    FFMPEG_COMMAND = config.ffmpeg.cmd_path_windows + FFMPEG_COMMAND_ARGS
else:
    FFMPEG_COMMAND = config.ffmpeg.cmd_path + FFMPEG_COMMAND_ARGS

logger = logging.getLogger(__name__)


class FfmpegTimeoutError(Exception):
    pass


class VReddit(Downloader):
    def __init__(self, url, *args, **kwargs):
        Downloader.__init__(self, url, *args, **kwargs)
        self._file_path = os.path.join('downloads', '{}.mp4'.format(self._identifier))

        self._url_audio = re.sub(r'\/DASH_.*$', '/audio', self._url)
        self._audio_size = 0
        self._audio_path = os.path.normpath(os.path.join('downloads', '{}.mp3'.format(self._identifier)))
        self._video_path = self._file_path
        self._merged_path = os.path.normpath(self._file_path.replace('.mp4', '_merged.mp4'))

    @property
    def audio_path(self):
        return self._audio_path

    @property
    def merged_path(self):
        return self._merged_path

    @property
    def url_audio(self):
        return self._url_audio

    def __repr__(self):
        return '<VReddit {} - {}>'.format(self._url, self._url_audio)

    def audio_url_forbidden(self):
        """Check whether the audio url is a working url or not.
        Sometimes v.reddit videos might have the is_gif property set to False, but
        still have no audio (see issue #91). So we have to do this additional check

        Inspired by https://stackoverflow.com/a/21515813
        """

        # https://stackoverflow.com/a/21515813
        try:
            urllib.request.urlopen(self._url_audio)
            return False
        except urllib.error.HTTPError as e:
            logger.error('audio url validity check: the url is forbidden (%s)', str(e))
            return True

    def remove(self, keep_thumbnail=False):
        # noinspection PyBroadException
        try:
            self._thumbnail_bo.close()
        except Exception:
            pass

        paths = [
            self._file_path,
            self._audio_path,
            self._merged_path
        ]
        if not keep_thumbnail:
            paths.append(self._thumbnail_path)

        for file_path in paths:
            logger.info('removing %s...', file_path)
            try:
                os.remove(file_path)
                logger.info('...%s removed', file_path)
            except FileNotFoundError:
                logger.error('...%s not removed: FileNotFoundError', file_path)

    def download_audio(self):
        u.download_file_stream(self._url_audio, self._audio_path)

        self._audio_size = os.path.getsize(self._audio_path)

        return self._audio_path

    def merge(self):
        cmd = FFMPEG_COMMAND.format(
            video=self._file_path,
            audio=self._audio_path,
            output=self._merged_path
        )

        dt_filename = u.now(string='%Y%m%d_%H%M')
        stdout_filepath = os.path.join('logs', 'ffmpeg', 'ffmpeg_stdout_{}.log'.format(dt_filename))
        stderr_filepath = os.path.join('logs', 'ffmpeg', 'ffmpeg_stderr_{}.log'.format(dt_filename))

        stdout_file = open(stdout_filepath, 'wb')
        stderr_file = open(stderr_filepath, 'wb')

        # subprocess.call(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

        timeout = 180
        sp = subprocess.Popen(cmd, shell=True, stdout=stdout_file, stderr=stderr_file)
        try:
            ffmpeg_start = u.now()
            logger.debug('ffmpeg command execution started: %s', u.now(string=TIME_FORMAT))

            sp.communicate(timeout=timeout)

            ffmpeg_end = u.now()
            ffmpeg_elapsed_seconds = (ffmpeg_end - ffmpeg_start).seconds
            logger.debug('ffmpeg command execution ended: %s (elapsed time (seconds): %d)', u.now(string=TIME_FORMAT), ffmpeg_elapsed_seconds)
        except subprocess.TimeoutExpired:
            logger.error(
                'subprocess.TimeoutExpired (%d seconds) error during ffmpeg command execution (see %s, %s)',
                timeout,
                str(stdout_filepath),
                str(stderr_filepath)
            )

            # we have to kill the subprocess, otherwise ffmpeg will keep the file open and we will not be able to delete it
            # https://docs.python.org/3/library/subprocess.html#subprocess.Popen.communicate
            logger.info('killing subprocess (pid: %d)...', sp.pid)
            sp.kill()

            stdout_file.close()
            stderr_file.close()

            # raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)
            raise FfmpegTimeoutError

        stdout_file.close()
        stderr_file.close()

        return self._merged_path
    
    def download_and_merge(self, skip_audio=False):
        self.download()
        if not skip_audio:
            # some vreddits don't have an audio (they are GIFs basically),
            # so we have to skip the audio download and merge
            self.download_audio()
            self.merge()

            self._size = os.path.getsize(self._merged_path)  # calculate the size again after audio and video are merged

            return self._merged_path  # return the merged video/audio path if we didn't skip the audio
        else:
            return self._file_path  # return the downloaded video path if we have skipped the audio
