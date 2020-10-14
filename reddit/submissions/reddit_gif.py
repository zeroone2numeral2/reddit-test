from pprint import pformat

from telegram import ParseMode, TelegramError
from telegram.error import BadRequest

from .video import Video


class RedditGif(Video):
    def __init__(self, *args, **kwargs):
        Video.__init__(self, *args, **kwargs)

        try:
            self._url = self._submission.preview['images'][0]['variants']['mp4']['resolutions'][-1]['url']
        except (KeyError, IndexError):
            self.log.debug('KeyError/IndexError while getting the i.reddit gif high resolution mp4 url. self._s.preview: %s\nusing submission.url instead...', pformat(self._submission.preview))
            self._url = self._submission.url

    @staticmethod
    def test(submission):
        if submission.domain == 'i.redd.it' and submission.url.endswith('.gif'):
            return True

        return False

    def _entry_point(self, caption, reply_markup=None):
        try:
            return self._bot.send_video(
                self._chat_id,
                self._url,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                timeout=360
            )
        except (BadRequest, TelegramError) as e:
            self.log.info(
                'i.reddit gif: TelegramError/BadRequest while sending by url (%s), falling back to self._send_video...',
                e.message)
            return self._send_video(caption, reply_markup=reply_markup)
