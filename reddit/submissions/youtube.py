from telegram import ParseMode

from ..downloaders import YouTube as YouTubeDownloader
from ..downloaders import YouTubeFileTooBig
from ..downloaders import YouTubeTooLong
from ..downloaders import YouTubeIsStreaming
from .base_submission import BaseSenderType


class YouTube(BaseSenderType):
    def __init__(self, *args, **kwargs):
        BaseSenderType.__init__(self, *args, **kwargs)
        self._url = self._submission.url

    @staticmethod
    def test(submission, subreddit):
        if ('youtube.com' in submission.domain_parsed or 'youtu.be' in submission.domain_parsed) and subreddit.youtube_download:
            return True

        return False

    def _entry_point(self, caption, reply_markup=None):
        self.log.info('youtube video url: %s', self._url)

        ytvideo = YouTubeDownloader(self._url, max_duration=self._subreddit.youtube_download_max_duration)
        # self.log.info('yt downloaded video path: %s', ytvideo.file_path)
        try:
            self.log.info('downloading youtube video...')
            ytvideo.download()
            self.log.info('...download ended. File size: %s', ytvideo.size_readable)
        except YouTubeFileTooBig:
            self.log.info('youtube video is too big to be sent (%s), removing file and sending text...',
                          ytvideo.size_readable)
            ytvideo.remove()

            raise YouTubeFileTooBig
        except YouTubeTooLong:
            self.log.info('youtube video is too long, removing file and sending text...')
            ytvideo.remove()

            raise YouTubeTooLong
        except YouTubeIsStreaming:
            self.log.info('youtube video is a streaming, removing file and sending text...')
            ytvideo.remove()

            raise YouTubeIsStreaming

        self.log.debug('opening and sending video...')
        with open(ytvideo.file_path, 'rb') as f:
            sent_message = self._bot.send_video(
                self.chat_id,
                f,
                caption=caption,
                thumb=ytvideo.thumb.file_bytes,
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
        ytvideo.remove()

        self._sum_uploaded_bytes(sent_message)

        return sent_message
