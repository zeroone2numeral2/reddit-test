import re

from telegram import ParseMode
from telegram import TelegramError

from utilities import u
from .base_submission import BaseSenderType
from ..downloaders import Image as ImageDownloader


class Image(BaseSenderType):
    def __init__(self, *args, **kwargs):
        BaseSenderType.__init__(self, *args, **kwargs)
        self._url = self._submission.url

    @staticmethod
    def test(submission):
        url_lower = submission.url.lower()

        if url_lower.endswith(('.jpg', '.png', '.jpeg')) or re.search(r'.+(?:\.jpg\?.+|\.jpeg\?.+|\.png\?.+)', url_lower):
            return True
        elif 'https://instagram.' in url_lower and '.jpg' in url_lower:
            return True
        elif 'artstation.com' in url_lower:
            return True
        elif 'images-wixmp' in url_lower:
            return True
        elif 'i.reddituploads.com' in url_lower:
            return True
        else:
            return False

    def _send_image_base(self, image, caption=None, reply_markup=None):
        return self._bot.send_photo(
            self._chat_id,
            photo=image,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            timeout=360
        )

    def _send_image_download(self, image_url, caption, reply_markup=None):
        self.log.info('downloading and sending image (image url: %s)', image_url)

        image = ImageDownloader(self._url)
        success = image.download(raise_exception=False)
        if not success:
            # failed to download: raise an exception
            raise BaseException('failed to send by url and to download file')

        sent_message = self._send_image_base(image=image.file_bytes, caption=caption, reply_markup=reply_markup)
        image.close()

        self._sum_uploaded_bytes(sent_message)

        return sent_message

    def _entry_point(self, caption, reply_markup=None):
        self.log.info('sending image by url (image url: %s)', self._url)

        start = u.now()
        try:
            sent_message = self._send_image_base(image=self._url, caption=caption, reply_markup=reply_markup)
        except TelegramError as e:
            # if sending by url fails, try to download the image and post it
            if 'failed to get http url content' not in e.message.lower() and 'wrong file identifier/http url specified' not in e.message.lower():
                raise e

            self.log.info('sending by url failed: trying to dowload image url')
            sent_message = self._send_image_download(self._url, caption=caption, reply_markup=reply_markup)

        end = u.now()
        self.log.debug('it took %d seconds to send the photo (%s)', (end - start).total_seconds(), self._url)

        return sent_message
