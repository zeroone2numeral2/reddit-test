from telegram import ParseMode

from ..downloaders import Downloader
from ..downloaders import FileTooBig
from .base_submission import BaseSenderType


class Video(BaseSenderType):
    def __init__(self, *args, **kwargs):
        BaseSenderType.__init__(self, *args, **kwargs)
        self._url = self._submission.url

    @staticmethod
    def test(submission):
        url_lower = submission.url.lower()
        if url_lower.endswith('.mp4'):
            return True

        return False

    def _send_video(self, caption, reply_markup=None):
        self.log.info('video url: %s', self._url)

        video = Downloader(self._url, identifier=self._submission.id)
        self.log.info('video path: %s', video.file_path)
        try:
            self.log.info('downloading video...')
            video.download()
            self.log.info('...download ended. File size: %s', video.size_readable)
        except FileTooBig:
            self.log.info('video is too big to be sent (%s), removing file and sending text...', video.size_readable)
            video.remove(keep_thumbnail=True)

            raise FileTooBig

        video.thumbnail_path = 'assets/video_thumb.png'  # generic thumbnail

        self.log.debug('opening and sending video...')
        with open(video.file_path, 'rb') as f:
            sent_message = self._bot.send_video(
                self._chat_id,
                f,
                caption=caption,
                thumb=video.get_thumbnail_bo(),
                height=None,
                width=None,
                duration=None,
                parse_mode=ParseMode.HTML,
                supports_streaming=True,
                reply_markup=reply_markup,
                timeout=360
            )
        self.log.debug('...upload completed')

        self.log.info('removing downloaded files...')
        video.remove(keep_thumbnail=True)
        # DO NOT DELETE THE GENERIC THUMBNAIL FILE

        self._sum_uploaded_bytes(sent_message)

        return sent_message

    def _entry_point(self, *args, **kwargs):
        # some other senders subclass this class and use _send_video
        return self._send_video(*args, **kwargs)
