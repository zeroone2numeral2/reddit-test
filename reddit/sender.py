import logging
import datetime

from telegram import ParseMode
from telegram.error import BadRequest
from telegram.error import TelegramError

from database.models import Post
from const import DEFAULT_TEMPLATE
from utilities import u

logger = logging.getLogger(__name__)


KEY_MAPPER_DICT = dict(
    created_utc=lambda timestamp: datetime.datetime.utcfromtimestamp(timestamp),
    created=lambda timestamp: datetime.datetime.fromtimestamp(timestamp)
)


class Sender(dict):
    def __init__(self, bot, channel, subreddit, submission):
        super(Sender, self).__init__()
        self._bot = bot
        self._submission = submission
        self._channel = channel
        self._subreddit = subreddit

        self._sent_message = None

        self._submission.is_image = False
        if self._submission.url.endswith(('.jpg', '.png')):
            self._submission.is_image = True

        self._submission.sorting = self._subreddit.sorting or 'hot'

        # if the post is a textual post, it will contain a "thread" inline url. Otherwise it will contain the "url"
        # and "comments" inline urls
        self._submission.permalink = 'https://www.reddit.com{}'.format(self._submission.permalink)
        if self._submission.permalink == self._submission.url:
            self._submission.textual = True
            self._submission.thread_or_urls = '<a href="{}">thread</a>'.format(self._submission.permalink)
        else:
            self._submission.textual = False
            self._submission.thread_or_urls = '<a href="{}">url</a> • <a href="{}">comments</a>'.format(
                self._submission.url,
                self._submission.permalink
            )

        self._submission.score_dotted = u.dotted(self._submission.score or 0)
        self._submission.num_comments_dotted = u.dotted(self._submission.num_comments or 0)

        self._submission.text = None
        self._submission.text_32 = None
        self._submission.text_160 = None
        self._submission.text_200 = None
        self._submission.text_256 = None
        if self._submission.selftext:
            self._submission.text = self._submission.selftext
            self._submission.text_32 = self._submission.selftext[:32]
            self._submission.text_160 = self._submission.selftext[:120]
            self._submission.text_200 = self._submission.selftext[:200]
            self._submission.text_256 = self._submission.selftext[:256]

        created_utc_dt = datetime.datetime.utcfromtimestamp(self._submission.created_utc)

        self._submission.title_escaped = u.escape(self._submission.title)
        self._submission.created_utc_formatted = created_utc_dt.strftime('%d/%m/%Y, %H:%M')

        self._submission.elapsed_seconds = (u.now() - created_utc_dt).seconds
        self._submission.elapsed_minutes = self._submission.elapsed_seconds / 60
        self._submission.elapsed_hours = self._submission.elapsed_minutes / 60

        # "n hours ago" if hours > 0, else "n minutes ago"
        if self._submission.elapsed_hours > 0:
            self._submission.elapsed_smart = '{} hours ago'.format(int(self._submission.elapsed_hours))
        else:
            self._submission.elapsed_smart = '{} minutes ago'.format(int(self._submission.elapsed_minutes))

        self._submission_dict = dict()

        for key in dir(self._submission):
            val = getattr(submission, key)
            self._submission_dict[key] = val
            if KEY_MAPPER_DICT.get(key, None):
                # replace the key in the dict of the mapping object edits that value
                self._submission_dict[key] = KEY_MAPPER_DICT[key](val)

    @property
    def submission(self):
        return self._submission

    @property
    def submission_dict(self):
        return self._submission_dict

    @property
    def template_keys(self):
        return [key for key in self._submission_dict.keys() if not key.startswith('_') and isinstance(self._submission_dict[key], (datetime.datetime, str, int))]

    @property
    def is_image(self):
        return self._submission.is_image

    def __getitem__(self, item):
        return self._submission_dict[item]

    def post(self):
        template = self._subreddit.template
        if not template:
            logger.info('no template: using the default one')
            template = DEFAULT_TEMPLATE

        text = template.format(**self._submission_dict)
        # logger.info('post text: %s', text)

        if self._submission.is_image and self._subreddit.send_images:
            logger.info('post is an image: using send_photo()')
            self._sent_message = self._send_image(self._submission.url, text, send_text_fallback=True)
        else:
            self._sent_message = self._send_text(text)

        return self._sent_message

    def _send_text(self, text):
        return self._bot.send_message(
            self._channel.channel_id,
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=not self._subreddit.webpage_preview
        )

    def _send_image(self, image_url, caption, send_text_fallback=True):
        try:
            self._sent_message = self._bot.send_photo(
                self._channel.channel_id,
                image_url,
                caption=caption,
                parse_mode=ParseMode.HTML,
                timeout=360
            )
            return self._sent_message
        except (BadRequest, TelegramError) as e:
            logger.error('Telegram error when sending photo: %s', e.message)
            if send_text_fallback:
                return self._send_text(caption)
    
    def register_post(self):
        Post.create(
            submission_id=self._submission.id,
            subreddit=self._subreddit,
            channel=self._channel,
            message_id=self._sent_message.message_id if self._sent_message else None,
            posted_at=u.now() if self._sent_message else None
        )
    
    def test_filters(self):
        if self._subreddit.ignore_stickied and self._submission.stickied:
            return False
        elif self._subreddit.images_only and not self.is_image:
            return False
        else:
            return True
        



