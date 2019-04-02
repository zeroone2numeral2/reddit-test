from telegram import ParseMode

from const import DEFAULT_ANNOUNCEMENT_TEMPLATE
from database.models import PostResume
from .sender import Sender
from utilities import u


class SenderResume(Sender):
    def __init__(self, *args, **kwargs):
        Sender.__init__(self, *args, **kwargs)

        self._s.resume_frequency = self._subreddit.frequency
        self._s.resume_posts = self._subreddit.number_of_posts

        self.gen_submission_dict()

    def post_resume_announcement(self):
        template = self._subreddit.resume_template
        if not template:
            template = DEFAULT_ANNOUNCEMENT_TEMPLATE

        text = template.format(**self._submission_dict)

        return self._bot.send_message(
            self._subreddit.channel.channel_id,
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=not self._subreddit.webpage_preview
        )

    def register_post(self):
        PostResume.create(
            submission_id=self._s.id,
            subreddit=self._subreddit,
            channel=self._subreddit.channel,
            message_id=self._sent_message.message_id if self._sent_message else None,
            posted_at=u.now() if self._sent_message else None
        )