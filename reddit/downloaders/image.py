import os
import tempfile

import requests

from bot.logging import slogger


class ImageDownloader:
    def __init__(self, image_url, use_stream=False, use_tempfile=True, file_name=None):
        self._url = image_url
        self._use_stream = use_stream
        self._tempfile_downloaded = None
        self._use_tempfile = use_tempfile
        self._size = None

        if self._use_tempfile:
            self._tempfile_downloaded = tempfile.TemporaryFile()

        # this is just for streams or if use_tempfile is False
        self._file_path = None

        if self._use_stream or not self._use_tempfile:
            if not file_name:
                raise ValueError('file_name needed if use_stream is true or use_tempfile is false')

            if not file_name.lower().endswith(('.jpg', '.png')):
                if self._url.lower().endswith('.png'):
                    file_name += '.png'
                else:
                    file_name += '.jpg'

            self._file_path = os.path.join('downloads', file_name)

    @property
    def file_bytes(self):
        if self._use_tempfile:
            self._tempfile_downloaded.seek(0)
            return self._tempfile_downloaded

        return open(self._file_path, 'rb')

    @property
    def size(self):
        if self._size is None:
            r = requests.get(self._url)
            self._size = int(r.headers.get('content-length', 0))

        return self._size

    @property
    def file_path(self):
        return self._file_path

    def set_size_from_headers(self, response: requests.Response):
        self._size = int(response.headers.get('content-length', 0))

    def download(self, *args, **kwargs):
        if self._use_stream:
            return self._download_stream(*args, **kwargs)
        else:
            return self._download(*args, **kwargs)

    def _download(self, raise_exception=False) -> bool:
        try:
            dloaded_file = requests.get(self._url)

            if self._use_tempfile:
                self._tempfile_downloaded.write(dloaded_file.content)
            else:
                with open(self._file_path, 'wb') as f:
                    f.write(dloaded_file.content)
        except Exception as e:
            if raise_exception:
                raise e
            else:
                slogger.info('execption while downloading url %s: %s', self._url, str(e), exc_info=True)
                return False

        return True

    # noinspection PyUnreachableCode
    def _download_stream(self, chunk_size=1024):
        raise NotImplementedError

        # https://stackoverflow.com/a/16696317

        # if not file_name:
        #     file_name = self._url.split('/')[-1]

        response = requests.get(self._url, stream=True)

        self.set_size_from_headers(response)

        with open(self._file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    # f.flush() commented by recommendation from J.F.Sebastian

        return self._file_path

    def close(self):
        if self._use_stream or not self._use_tempfile:
            try:
                os.remove(self._file_path)
            except Exception as e:
                slogger.error('error while trying to delete downloaded file %s: %s', self._file_path, str(e))
        elif self._use_tempfile:
            try:
                self._tempfile_downloaded.close()
            except Exception as e:
                slogger.error('error while trying to close downloaded tempfile: %s', str(e))
