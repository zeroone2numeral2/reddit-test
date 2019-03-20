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

        self._submission.flair_with_space = ''
        if self._submission.link_flair_text is not None:
            self._submission.flair_with_space = '[{}] '.format(self._submission.link_flair_text)

        self._submission.nsfw = self._submission.over_18

        self._submission.sorting = self._subreddit.sorting or 'hot'

        self._submission.comments_url = 'https://www.reddit.com{}'.format(self._submission.permalink)

        # if the post is a textual post, it will contain a "thread" inline url. Otherwise it will contain the "url"
        # and "comments" inline urls
        if self._submission.comments_url == self._submission.url:
            self._submission.textual = True
            self._submission.thread_or_urls = '<a href="{}">thread</a>'.format(self._submission.comments_url)
        else:
            self._submission.textual = False
            self._submission.thread_or_urls = '<a href="{}">url</a> • <a href="{}">comments</a>'.format(
                self._submission.url,
                self._submission.comments_url
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
        self._submission.elapsed_smart = u.elapsed_time_smart(self._submission.elapsed_seconds)

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
            logger.info('tests failed: sticked submission')
            return False
        elif self._subreddit.images_only and not self.is_image:
            logger.info('tests failed: subreddit is not an image')
            return False
        elif self._subreddit.min_score and isinstance(self._subreddit.min_score, int) and self._subreddit.min_score > self._submission.score:
            logger.info('tests failed: not enough upvotes (%d/%d)', self._submission.score, self._subreddit.min_score)
            return False
        elif self._subreddit.ignore_if_newer_than \
                and isinstance(self._subreddit.ignore_if_newer_than, datetime.datetime) \
                and ((u.now() - self._submission.created_utc).seconds / 60) < self._subreddit.ignore_if_newer_than:
            logger.info('tests failed: too new (submitted: %s)', self._submission.created_utc_formatted)
            return False
        else:
            return True
        



