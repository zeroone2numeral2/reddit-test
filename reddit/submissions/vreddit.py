import re

from telegram import ParseMode

from ..downloaders import FileTooBig
from ..downloaders import VReddit as VRedditDownloader
from ..downloaders.vreddit import FfmpegTimeoutError
from const import MaxSize
from .base_submission import BaseSenderType


class VReddit(BaseSenderType):
    def __init__(self, *args, **kwargs):
        BaseSenderType.__init__(self, *args, **kwargs)
        self._url = self._submission.media['reddit_video']['fallback_url']
        self._video_size = (
            self._submission.media['reddit_video']['height'],
            self._submission.media['reddit_video']['width']
        )
        self._video_duration = self._submission.media['reddit_video']['duration']
        self._submission.is_gif = self._submission.media['reddit_video'].get('is_gif', False)  # some v.reddit might not have audio

    @staticmethod
    def test(submission):
        if submission.is_video and 'reddit_video' in submission.media:
            return True

        return False

    def _entry_point(self, caption, reply_markup=None):
        self.log.info('vreddit url: %s', self._url)

        # we set as max_size the max size supported by the bot API, so we can avoid to use pyrogram (see issue #82)
        vreddit = VRedditDownloader(self._url, thumbnail_url=self._submission.thumbnail, identifier=self._submission.id, max_size=MaxSize.MTPROTO_LIMITED,
                                    logger=self.log)
        self.log.info('vreddit video url: %s', vreddit.url)
        self.log.info('vreddit audio url: %s', vreddit.url_audio)

        if self._submission.is_gif:
            self.log.info(
                '[1/2] vreddit is a GIF (does not have an audio): we will NOT try to download the audio and merge audio and video')
            self.log.info(
                '[2/2] the following logs will mention the merged audio/video, but we are now just handling the video')

        video_without_audio = False  # we should check here if the audio url is a webpage (issue #91)
        if self._submission.is_gif or vreddit.audio_url_forbidden():
            self.log.info('this vreddit does not have an audio, we will skip the audio download (is_gif: %s)',
                          self._submission.is_gif)
            video_without_audio = True

        file_path = vreddit.file_path
        self.log.info('file that will be used for the merged audio/video: %s', vreddit.merged_path)
        try:
            self.log.info('downloading video/audio and merging them...')
            file_path = vreddit.download_and_merge(skip_audio=video_without_audio)
            self.log.info('...merging ended. File size: %s', vreddit.size_readable)
            self.log.info('file path of the video we will send: %s', file_path)
        except FileTooBig:
            self.log.info('video is too big to be sent (%s), removing file and sending text...', vreddit.size_readable)
            vreddit.remove()
            raise FileTooBig
        except FfmpegTimeoutError:
            self.log.info('ffmpeg timeout error during the merging of video/audio')
            vreddit.remove()
            raise FfmpegTimeoutError

        self.log.info('downloading thumbnail from url: %s', vreddit.thumbnail_url)
        vreddit.download_thumbnail()
        self.log.info('thumbnail path: %s', vreddit.thumbnail_path)

        video_args = dict(
            caption=caption,
            parse_mode=ParseMode.HTML,
            thumb_path=vreddit.thumbnail_path,
            thumb_bo=vreddit.get_thumbnail_bo(),
            height=self._video_size[0],
            width=self._video_size[1],
            duration=self._video_duration,
            supports_streaming=True,
            reply_markup=reply_markup,
            timeout=360
        )

        sent_message = self._upload_video(
            self.chat_id, file_path,
            file_size=vreddit.size,
            force_bot_api=False,  # True is used because of issue #82
            **video_args
        )

        self.log.info('removing downloaded files...')
        vreddit.remove()

        self._sum_uploaded_bytes(sent_message)

        return sent_message
