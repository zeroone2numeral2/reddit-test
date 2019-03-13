import logging
import datetime

from telegram import ParseMode
from telegram.error import BadRequest
from telegram.error import TelegramError

from utilities import u

logger = logging.getLogger(__name__)


DEFAULT_TEMPLATE = """\
<b>{title_escaped}</b>

<i>u/{author} • {elapsed_smart} • score: {score}</i>
#{subreddit} • <a href="{url}">content</a> • <a href="{permalink}">comments</a> ({num_comments})"""


KEY_MAPPER_DICT = dict(
    permalink=lambda x: 'https://www.reddit.com/{}'.format(x),
    created_utc=lambda timestamp: datetime.datetime.utcfromtimestamp(timestamp),
    created=lambda timestamp: datetime.datetime.fromtimestamp(timestamp)
)


class Sender(dict):
    def __init__(self, bot, channel, submission):
        super(Sender, self).__init__()
        self._bot = bot
        self._submission = submission
        # self.__dict__ = self._submission

        self._channel = channel

        self._submission.is_image = False
        if self._submission.url.endswith(('.jpg', '.png')):
            self._submission.is_image = True

        self._submission.textual = False
        if self._submission.permalink == self._submission.url:
            self._submission.textual = True

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
        return [key for key in self._submission_dict.keys() if not key.startswith('_') and isinstance(self._submission_dict[key], (datetime.datetime, str))]

    def __getitem__(self, item):
        return self._submission_dict[item]

    def post(self):
        template = self._channel.template
        if not template:
            logger.info('no template: using the default one')
            template = DEFAULT_TEMPLATE

        text = template.format(**self._submission_dict)

        if self._submission.is_image and self._channel.send_images:
            logger.info('post is an image: using send_photo()')
            sent_message = self._send_image(self._submission.url, text, send_text_fallback=True)
        else:
            sent_message = self._send_text(text)

        return sent_message

    def _send_text(self, text):
        return self._bot.send_message(
            self._channel.channel_id,
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=not self._channel.webpage_preview
        )

    def _send_image(self, image_url, caption, send_text_fallback=True):
        try:
            return self._bot.send_photo(
                self._channel.channel_id,
                image_url,
                caption=caption,
                parse_mode=ParseMode.HTML,
                timeout=360
            )
        except (BadRequest, TelegramError) as e:
            logger.error('Telegram error when sending photo: %s', e.message)
            if send_text_fallback:
                self._send_text(caption)



