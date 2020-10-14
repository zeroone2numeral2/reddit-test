from telegram import ParseMode

from .base_submission import BaseSenderType


class Gif(BaseSenderType):
    def __init__(self, *args, **kwargs):
        BaseSenderType.__init__(self, *args, **kwargs)
        self._url = self._submission.url
        self._ulr = self._url.lower().replace('.gifv', '.mp4')

    @staticmethod
    def test(submission):
        url_lower = submission.url.lower()
        if url_lower.endswith('.gifv'):
            return True

        return False

    def _entry_point(self, caption, reply_markup=None):
        self.log.info('gif url: %s', self._url)

        return self._bot.send_animation(
            self._chat_id,
            self._url,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            timeout=360
        )
