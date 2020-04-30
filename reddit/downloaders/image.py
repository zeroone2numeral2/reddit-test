import logging
import urllib.request as urllib
import tempfile

logger = logging.getLogger(__name__)


class Image:
    def __init__(self, image_url, use_stream=False):
        self._url = image_url
        self._use_stream = use_stream
        self._tempfile_downloaded = tempfile.SpooledTemporaryFile()

    @property
    def file_bytes(self):
        self._tempfile_downloaded.seek(0)
        return self._tempfile_downloaded

    def download(self, raise_exception=False) -> bool:
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

    def close(self):
        try:
            self._tempfile_downloaded.close()
        except Exception as e:
            logger.error('error while trying to close downloaded tempfile: %s', str(e))
