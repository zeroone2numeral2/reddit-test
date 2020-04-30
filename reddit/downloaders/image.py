import logging
import os
import urllib.request as urllib
import tempfile

import requests

logger = logging.getLogger(__name__)


class Image:
    def __init__(self, image_url, use_stream=False):
        self._url = image_url
        self._use_stream = use_stream
        self._tempfile_downloaded = tempfile.SpooledTemporaryFile()
        self._size = None

        # this is just for streams
        self._file_path = None

    @property
    def file_bytes(self):
        self._tempfile_downloaded.seek(0)
        return self._tempfile_downloaded

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
            dloaded_file = urllib.urlopen(self._url)
            self._tempfile_downloaded = dloaded_file.read()
        except Exception as e:
            if raise_exception:
                raise e
            else:
                logger.info('execption while downloading url %s: %s', self._url, str(e), exc_info=True)
                return False

        return True

    # noinspection PyUnreachableCode
    def _download_stream(self, file_name=None, chunk_size=1024):
        raise NotImplementedError

        # https://stackoverflow.com/a/16696317

        if not file_name:
            file_name = self._url.split('/')[-1]

        self._file_path = os.path.join('downloads', file_name)

        response = requests.get(self._url, stream=True)

        self.set_size_from_headers(response)

        with open(self._file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    # f.flush() commented by recommendation from J.F.Sebastian

        return self._file_path

    def close(self):
        try:
            self._tempfile_downloaded.close()
        except Exception as e:
            logger.error('error while trying to close downloaded tempfile: %s', str(e))

        try:
            os.remove(self._file_path)
        except Exception as e:
            logger.error('error while trying to delete downloaded file %s: %s', self._file_path, str(e))
