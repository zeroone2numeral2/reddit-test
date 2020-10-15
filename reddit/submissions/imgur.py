from telegram import InputMediaPhoto, InputMediaAnimation, InputMediaVideo
from telegram import ParseMode

from ..downloaders import Imgur as ImgurDownloader
from .base_submission import BaseSenderType
from config import config

imgur = ImgurDownloader(config.imgur.id, config.imgur.secret)


class ImgurGallery(BaseSenderType):
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
        kwargs = dict(chat_id=self._chat_id, media=media, reply_markup=reply_markup, timeout=360)
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
                url = url.replace('.gif', '.mp4')
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
