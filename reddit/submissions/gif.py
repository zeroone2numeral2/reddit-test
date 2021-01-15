from telegram import ParseMode

from .base_submission import BaseSenderType


class GifHandler(BaseSenderType):
    def __init__(self, *args, **kwargs):
        BaseSenderType.__init__(self, *args, **kwargs)
        self._url = self._submission.url

        if self._url.endswith('.gifv'):
            self._url = self._url.replace('.gifv', '.mp4')
        elif self._url.endswith('.gif'):
            self._url = self._url.replace('.gif', '.mp4')

    @staticmethod
    def test(submission):
        url_lower = submission.url.lower()
        if 'imgur.com' in url_lower and url_lower.endswith(('.gifv', '.gif')):
            return True

        return False

    def _entry_point(self, caption, reply_markup=None):
        self.log.info('gif url: %s', self._url)

        return self._bot.send_animation(
            self.chat_id,
            self._url,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            timeout=360
        )
