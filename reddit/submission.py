import logging

from telegram import ParseMode

logger = logging.getLogger(__name__)


DEFAULT_TEMPLATE = """\
[#{subreddit}] <b>{title}</b>

{from} at {created_utc} • score: {score} (<i>{sorting}</i>)
<a href="{url}">content</a> • <a href="{permalink}">comments</a> ({num_comments})"""


class SubmissionObject(dict):
    def __init__(self, submission, channel):
        super(SubmissionObject, self).__init__()
        self.submission = submission
        self.__dict__ = self.submission

        self._channel = channel
        self._is_image = False

        if self.submission.url.endswith(('.jpg', '.png')):
            self._is_image = False

    def post(self, bot):
        template = self._channel.template
        if not template:
            template = DEFAULT_TEMPLATE

        text = template.format(**self)

        if self._is_image and self._channel.send_images:
            sent_message = self._send_image(self.submission.url, text)
        else:
            sent_message = bot.send_message(
                self._channel.channel_id,
                text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=not self._channel.webpage_preview
            )

        self._update_channel_last_post_dt()

        return sent_message


    def _send_image(self, image_url, caption):
        pass

    def _update_channel_last_post_dt(self):
        raise NotImplementedError




