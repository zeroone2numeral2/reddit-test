from telegram import InputMediaPhoto
from telegram import ParseMode
from telegram import TelegramError

from .base_submission import BaseSenderType
from ..downloaders import Image


class GalleryImages(BaseSenderType):
    def __init__(self, *args, **kwargs):
        BaseSenderType.__init__(self, *args, **kwargs)

    @staticmethod
    def test(submission):
        if not hasattr(submission, 'gallery_data'):
            return False

        for media_id, media_metadata in submission.media_metadata.items():
            if media_metadata['e'] != 'Image':
                # if even a single media is not an image, the test fails
                return False

        return True

    @staticmethod
    def _fetch_urls(media_metadata, use_largest_preview=False, limit=10):
        urls = list()
        for media_id, media_metadata in media_metadata.items():
            if not use_largest_preview:
                # 's': dicts that contains the actual image
                # image_url = media_metadata['s']['u']
                # alternative way of getting the image url:
                image_url = 'https://i.redd.it/{}.jpg'.format(media_id)
            else:
                # 'p': dicts that contains a list of previews (we use the largest one)
                image_url = media_metadata['p'][-1]['u']

            urls.append(image_url)

            if limit and len(urls) == limit:
                break

        return urls

    def _send_gallery_images_base(self, media, reply_markup=None):
        kwargs = dict(chat_id=self._chat_id, media=media, reply_markup=reply_markup, timeout=360)
        return self._bot.send_media_group(**kwargs)

    def send_gallery_images_download(self, caption, reply_markup=None):
        self.log.info('downloading and sending images gallery (gallery url: %s)', self._submission.url)

        media_group = list()
        urls = self._fetch_urls(self._submission.media_metadata)

        for url in urls:
            image = Image(url)
            success = image.download(raise_exception=False)
            if not success:
                self.log.error('failed to send by url and to download file')
                continue

            media_group.append(InputMediaPhoto(media=image.file_bytes, caption=None if len(media_group) != 0 else caption,
                                               parse_mode=ParseMode.HTML))

        if not media_group:
            # raise an exception if the gallery is empty
            raise ValueError('sending gallery by downloading its images: MediaGroup is empty')

        sent_messages = self._send_gallery_images_base(media=media_group, reply_markup=reply_markup)

        self._sum_uploaded_bytes(sent_messages)

        return sent_messages

    def _entry_point(self, caption, reply_markup=None):
        self.log.info('sending gallery of images by url (gallery url: %s)', self._submission.url)

        urls = self._fetch_urls(self._submission.media_metadata)
        media_group = [InputMediaPhoto(media=url, caption=None if i != 0 else caption, parse_mode=ParseMode.HTML) for
                       i, url in enumerate(urls)]

        try:
            sent_messages = self._send_gallery_images_base(media=media_group, reply_markup=reply_markup)
        except TelegramError as e:
            # if sending by url fails, try to download the images and post them
            if 'failed to get http url content' not in e.message.lower() and 'wrong file identifier/http url specified' not in e.message.lower():
                raise e

            self.log.info('sending by url failed: trying to dowload gallery from its urls')
            sent_messages = self.send_gallery_images_download(caption=caption, reply_markup=reply_markup)

        return sent_messages
