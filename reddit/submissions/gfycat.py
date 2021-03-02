from telegram import ParseMode, TelegramError

from ..downloaders import GfycatDownloader
from .base_submission import BaseSenderType


class GfycatHandler(BaseSenderType):
    def __init__(self, *args, **kwargs):
        BaseSenderType.__init__(self, *args, **kwargs)
        self._url = self._submission.url

    @staticmethod
    def test(submission):
        if 'gfycat.com' in submission.domain_parsed.lower():
            return True

        return False

    def _send_by_url(self, url, request_kwargs):
        request_kwargs["video"] = url

        return self._bot.send_video(**request_kwargs)

    def _send_by_file_path(self, file_path, request_kwargs):

        with open(file_path, 'rb') as f:
            request_kwargs["video"] = f
            sent_message = self._bot.send_video(**request_kwargs)

        return sent_message

    def _entry_point(self, caption, reply_markup=None):
        gfycat = GfycatDownloader(self._url)
        self.log.info('gfycat url: %s', gfycat.url)

        gfycat.download_thumbnail()

        request_kwargs = dict(
            chat_id=self.chat_id,
            caption=caption,
            parse_mode=ParseMode.HTML,
            width=gfycat.sizes[0],
            height=gfycat.sizes[1],
            thumb=gfycat.get_thumbnail_bo(),
            duration=gfycat.duration,
            reply_markup=reply_markup,
            timeout=360
        )

        try:
            sent_message = self._send_by_url(gfycat.url, request_kwargs)
        except TelegramError as e:
            if "http url specified" not in e.message.lower():
                raise e

            self.log.info('sending by url failed (%s), downloading and uploading as video...', e.message)
            gfycat.download()

            sent_message = self._send_by_file_path(gfycat.file_path, request_kwargs)

        gfycat.remove()

        return sent_message
