import re
import logging

from telegram import InputMediaPhoto, InputMediaVideo
from telegram import ParseMode
from imgurpython.helpers.error import ImgurClientError

from ..downloaders import Imgur as ImgurDownloader
from .base_submission import BaseSenderType
from .image import ImageHandler
from .gif import GifHandler
from .video import VideoHandler
from config import config

logger = logging.getLogger(__name__)

imgur = ImgurDownloader(config.imgur.id, config.imgur.secret)


class ImgurGalleryHandler(BaseSenderType):
    def __init__(self, *args, **kwargs):
        BaseSenderType.__init__(self, *args, **kwargs)

        self._urls = imgur.parse_album(self._submission.url)
        self._gallery_url = self._submission.url

    @staticmethod
    def test(submission):
        url_lower = submission.url.lower()
        if 'imgur.com/gallery' in url_lower or 'imgur.com/a/' in url_lower:
            return True

        return False

    def _send_album_base(self, media, reply_markup=None):
        kwargs = dict(chat_id=self.chat_id, media=media, reply_markup=reply_markup, timeout=360)
        return self._bot.send_media_group(**kwargs)

    def _entry_point(self, caption, reply_markup=None):
        self.log.info('sending gallery of images by url (gallery url: %s)', self._submission.url)

        media_group = list()
        for i, url in enumerate(self._urls):
            if url.endswith(('.jpg', '.png')):
                input_media = InputMediaPhoto(media=url, caption=None if i != 0 else caption, parse_mode=ParseMode.HTML)
            elif url.endswith('.mp4'):
                input_media = InputMediaVideo(media=url, caption=None if i != 0 else caption, parse_mode=ParseMode.HTML)
            elif url.endswith('.gifv'):
                url = url.replace('.gifv', '.mp4')
                input_media = InputMediaVideo(media=url, caption=None if i != 0 else caption, parse_mode=ParseMode.HTML)
            elif url.endswith('.gif'):
                url = url.replace('.gif', '.mp4')  # sometimes some .gif urls, when converted to .mp4, return a static image
                input_media = InputMediaVideo(media=url, caption=None if i != 0 else caption, parse_mode=ParseMode.HTML)
            else:
                self.log.error('unknow Imgur media url found in gallery %s: %s', self._gallery_url, url)
                continue

            media_group.append(input_media)

            if i == 9:
                break

        if not media_group:
            raise ValueError('media_group is empty')

        sent_messages = self._send_album_base(media=media_group, reply_markup=reply_markup)

        return sent_messages


class ImgurNonDirectUrl:
    NON_DIRECT_URL_PATTERN = r'imgur.com/([a-z1-9]+)$'
    EXTENSIONS = ('.jpg', '.png', '.gif', 'gifv', '.mp4')

    def __init__(self, url):
        self._url = self.extract_direct_url(url)

    @staticmethod
    def extract_direct_url(url):
        imgur_id = re.search(ImgurNonDirectUrlImageHandler.NON_DIRECT_URL_PATTERN, url, re.I).group(1)
        direct_url = imgur.get_url(imgur_id)

        return direct_url

    @classmethod
    def test(cls, submission):
        url = submission.url
        url_lower = url.lower()
        if re.search(ImgurNonDirectUrlImageHandler.NON_DIRECT_URL_PATTERN, url_lower):
            # noinspection PyBroadException
            try:
                url = ImgurNonDirectUrlImageHandler.extract_direct_url(url)
            except ImgurClientError as e:
                logger.error('could not extract direct imgur url (%s): %s', url, str(e), exc_info=False)
                return False

            if url.endswith(cls.EXTENSIONS):
                return True

        return False


class ImgurNonDirectUrlImageHandler(ImgurNonDirectUrl, ImageHandler):
    EXTENSIONS = ('.jpg', '.png')

    def __init__(self, *args, **kwargs):
        ImageHandler.__init__(self, *args, **kwargs)
        ImgurNonDirectUrl.__init__(self, self._url)


class ImgurNonDirectUrlGifHandler(ImgurNonDirectUrl, GifHandler):
    EXTENSIONS = ('.gifv', '.gif')

    def __init__(self, *args, **kwargs):
        GifHandler.__init__(self, *args, **kwargs)
        ImgurNonDirectUrl.__init__(self, self._url)


class ImgurNonDirectUrlVideoHandler(ImgurNonDirectUrl, VideoHandler):
    EXTENSIONS = ('.mp4', '.gifv', '.gif')

    def __init__(self, *args, **kwargs):
        VideoHandler.__init__(self, *args, **kwargs)
        ImgurNonDirectUrl.__init__(self, self._url)

        self._url = self._url.replace('.gifv', '.mp4').replace('.gif', '.mp4')
