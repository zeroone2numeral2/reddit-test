from telegram import ParseMode

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

    def _entry_point(self, caption, reply_markup=None):
        gfycat = GfycatDownloader(self._url)
        self.log.info('gfycat url: %s', gfycat.url)

        gfycat.download_thumbnail()

        sent_message = self._bot.send_video(
            self.chat_id,
            gfycat.url,
            caption=caption,
            parse_mode=ParseMode.HTML,
            width=gfycat.sizes[0],
            height=gfycat.sizes[1],
            thumb=gfycat.get_thumbnail_bo(),
            duration=gfycat.duration,
            reply_markup=reply_markup,
            timeout=360
        )

        gfycat.remove()

        return sent_message
