from telegram import ParseMode
from telegram import Message as PtbMessage
from pyrogram import Message as PyroMessage

from const import DEFAULT_ANNOUNCEMENT_TEMPLATE
from database.models import PostResume
from .sender import Sender
from utilities import u


class SenderResume(Sender):
    def __init__(self, *args, **kwargs):
        Sender.__init__(self, *args, **kwargs)

        self._submission.resume_frequency = self._subreddit.frequency
        self._submission.resume_posts = self._subreddit.number_of_posts

        self.gen_submission_dict()

    def post_resume_announcement(self):
        template = self._subreddit.style.template_resume
        if not template:
            template = DEFAULT_ANNOUNCEMENT_TEMPLATE

        text = template.format(**self._submission_dict)

        return self._bot.send_message(
            self._subreddit.channel.channel_id,
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=not self._subreddit.style.webpage_preview
        )

    def register_post(self, test=False):
        if test:
            self.log.info('not creating PostResume row: %s is a testing subreddit', self._subreddit.r_name_with_id)
            return

        if isinstance(self._sent_message, PtbMessage):
            sent_message_json = self._sent_message.to_json()
        elif isinstance(self._sent_message, PyroMessage):
            sent_message_json = str(self._sent_message)
        else:
            sent_message_json = None

        self.log.info('creating PostResume row...')
        PostResume.create(
            submission_id=self._submission.id,
            subreddit=self._subreddit,
            channel=self._subreddit.channel,
            message_id=self._sent_message.message_id if self._sent_message else None,
            posted_at=u.now() if self._sent_message else None,
            sent_message=sent_message_json
        )