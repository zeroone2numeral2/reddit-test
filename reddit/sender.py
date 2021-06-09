import json
import logging
import datetime
import os
from collections import OrderedDict
from pprint import pformat
from urllib.parse import urlparse

from telegram import Bot
from telegram import Message as PtbMessage
from pyrogram import Message as PyroMessage

from database import db
from .submissions import TextHandler
from .submissions import GalleryImagesHandler
from .submissions import ImageHandler
from .submissions import VRedditHandler
from .submissions import VideoHandler
from .submissions import GfycatHandler
from .submissions import GifHandler
from .submissions import ImgurGalleryHandler, ImgurNonDirectUrlImageHandler, ImgurNonDirectUrlVideoHandler
from .submissions import RedditGifHandler
from .submissions import YouTubeHandler
from bot.markups import InlineKeyboard
from database.models import Post
from database.models import Subreddit
from database.queries import flairs
from const import DEFAULT_TEMPLATE
from utilities import u
from config import config

logger = logging.getLogger('sp')

KEY_MAPPER_DICT = dict(
    created_utc=lambda timestamp: datetime.datetime.utcfromtimestamp(timestamp),
    created=lambda timestamp: datetime.datetime.fromtimestamp(timestamp)
)

HIDDEN_CHAR = u'\u200B'

DEFAULT_FLAIR = "no_flair"

DEFAULT_THUMBNAILS = {
    # https://old.reddit.com/r/redditdev/comments/2wwuje/what_does_it_mean_when_the_thumbnail_field_has/
    'self': 'https://www.reddit.com/static/self_default2.png',
    'nsfw': 'https://www.reddit.com/static/nsfw2.png',
    'default': 'https://www.reddit.com/static/noimage.png',
    'spoiler': 'https://www.reddit.com/static/self_default2.png'  # this is actually not the correct icon
}

SUBSCRIPT = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")  # https://stackoverflow.com/a/24392215
SUPERSCRIPT = str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")


class Sender:
    __slots__ = ['_bot', '_subreddit', '_submission', '_sent_messages', '_uploaded_bytes', '_chat_id', '_submission_dict', 'log',
                 'submission_handler', 'submission_handler_text']

    def __init__(self, bot, subreddit, submission, skip_sender_type_detection=False):
        self._bot: Bot = bot
        self._submission = submission
        self._subreddit: Subreddit = subreddit
        if hasattr(subreddit, 'logger'):
            self.log = subreddit.logger
        else:
            self.log = logger

        self._sent_messages = []
        self._uploaded_bytes = 0
        sender_kwargs = dict(submission=self._submission, subreddit=self._subreddit, bot=self._bot)
        self.submission_handler_text = TextHandler(**sender_kwargs)
        self.submission_handler = TextHandler(**sender_kwargs)

        self._submission.flair_normalized = ''  # ascii flair
        self._submission.ascii_flair = DEFAULT_FLAIR  # ascii flair, will be "no_flair" when submission doesn't have a falir
        self._submission.nsfw = self._submission.over_18
        self._submission.sorting = self._subreddit.sorting or 'hot'
        self._submission.comments_url = 'https://www.reddit.com{}'.format(self._submission.permalink)
        self._submission.hidden_char = HIDDEN_CHAR  # we might need it for some templates
        self._submission.hidden_url_comments = '<a href="{}">{}</a>'.format(self._submission.comments_url, HIDDEN_CHAR)
        self._submission.score_dotted = u.dotted(self._submission.score or 0)
        self._submission.num_comments = int(self._submission.num_comments)
        self._submission.num_comments_dotted = u.dotted(self._submission.num_comments or 0)
        self._submission.domain_parsed = urlparse(self._submission.url).netloc
        self._submission.title_escaped = u.escape(self._submission.title)
        self._submission.text = ''
        self._submission.text_32 = ''
        self._submission.text_160 = ''
        self._submission.text_200 = ''
        self._submission.text_256 = ''
        self._submission.video_size = (None, None)
        self._submission.video_duration = 0
        self._submission.upvote_perc = int(self._submission.upvote_ratio * 100)
        self._submission.upvote_perc_subscript = str(self._submission.upvote_perc).translate(SUBSCRIPT)
        self._submission.upvote_perc_superscript = str(self._submission.upvote_perc).translate(SUPERSCRIPT)
        self._submission.author_username_lower = str(self._submission.author).lower()
        self._submission_dict = dict()

        # for crossposts: only the reference to the original post contains the 'media' attribute of the submission.
        # We can get the parent submission of the crosspost from `submission.crosspost_parent_list[0]`
        # and then we can add it to the crossposted submission
        self._submission.is_xpost = False
        self._submission.xpost_from = ''
        self._submission.xpost_from_string = ''
        if hasattr(self._submission, 'crosspost_parent') and len(self._submission.crosspost_parent_list) > 0:
            self._submission.is_xpost = True
            # sometimes submissions has the 'crosspost_parent' but there's no item in 'crosspost_parent_list'
            self.log.info('note: submission is a crosspost of %s (overriding media attributes...)',
                          self._submission.crosspost_parent)
            self._submission.xpost_from = self._submission.crosspost_parent_list[0].get('subreddit', '')
            self._submission.media = self._submission.crosspost_parent_list[0].get('media', None)
            self._submission.is_video = self._submission.crosspost_parent_list[0].get('is_video', False)
            self._submission.thumbnail = self._submission.crosspost_parent_list[0].get('thumbnail', None)
            self._submission.gallery_data = self._submission.crosspost_parent_list[0].get('gallery_data', None)
            self._submission.media_metadata = self._submission.crosspost_parent_list[0].get('media_metadata', None)

            if self._submission.url.startswith("/r/"):
                # for xposts to a reddit TEXTUAL thread, the "url" property is the xposted
                # thread link without the "https://reddit.com/"
                # in this case, we add the "https://reddit.com/" part and link the thread
                self.log.info("submission is an x-post of a textual reddit post")
                self._submission.url = "https://reddit.com" + self._submission.url

        # we need to do this after we check if the post is an x-post
        self._submission.hidden_url = '<a href="{}">{}</a>'.format(self._submission.url, HIDDEN_CHAR)

        if self._submission.thumbnail and self._submission.thumbnail.lower() in DEFAULT_THUMBNAILS:
            # https://old.reddit.com/r/redditdev/comments/2wwuje/what_does_it_mean_when_the_thumbnail_field_has/
            self._submission.thumbnail = DEFAULT_THUMBNAILS[self._submission.thumbnail.lower()]
        elif not self._submission.thumbnail:
            self._submission.thumbnail = 'https://www.reddit.com/static/noimage.png'

        if self._submission.link_flair_text is not None:
            ascii_flair = u.to_ascii(str(self._submission.link_flair_text), replace_spaces=True, lowercase=True)
            self._submission.flair_normalized = ascii_flair
            self._submission.ascii_flair = ascii_flair

        # if the post is a textual post, it will contain a "thread" inline url. Otherwise it will contain the "url"
        # and "comments" inline urls
        if self._submission.comments_url == self._submission.url:
            self._submission.textual = True
            self._submission.thread_or_urls = '<a href="{}">thread</a>'.format(self._submission.comments_url)
            self._submission.force_disable_link_preview = True
        else:
            self._submission.textual = False
            self._submission.thread_or_urls = '<a href="{}">url</a> • <a href="{}">comments</a>'.format(
                self._submission.url,
                self._submission.comments_url
            )
            self._submission.force_disable_link_preview = False

        if self._submission.selftext:
            text_len = len(self._submission.selftext)
            self._submission.text = self._submission.selftext
            self._submission.text_32 = '{}{}'.format(self._submission.selftext[:32], '' if text_len <= 32 else ' [...]')
            self._submission.text_160 = '{}{}'.format(self._submission.selftext[:160], '' if text_len <= 160 else ' [...]')
            self._submission.text_200 = '{}{}'.format(self._submission.selftext[:200], '' if text_len <= 200 else ' [...]')
            self._submission.text_256 = '{}{}'.format(self._submission.selftext[:256], '' if text_len <= 256 else ' [...]')

        created_utc_dt = datetime.datetime.utcfromtimestamp(self._submission.created_utc)
        self._submission.created_utc_formatted = created_utc_dt.strftime('%d/%m/%Y, %H:%M')

        self._submission.elapsed_seconds = (u.now() - created_utc_dt).total_seconds()
        self._submission.elapsed_minutes = int(round(self._submission.elapsed_seconds / 60))
        self._submission.elapsed_hours = int(round(self._submission.elapsed_minutes / 60))

        # "n hours ago" if hours > 0, else "n minutes ago"
        self._submission.elapsed_smart = u.elapsed_time_smart(self._submission.elapsed_seconds)
        self._submission.elapsed_smart_compact = u.elapsed_smart_compact(self._submission.elapsed_seconds)

        self._submission.index_channel_link = None
        self._submission.index_channel_username = None
        if config.telegram.get('index', False):
            self._submission.index_channel_link = 'https://t.me/{}'.format(config.telegram.index)
            self._submission.index_channel_username = '@{}'.format(config.telegram.index)

        self._submission.channel_invite_link = self._subreddit.channel_link
        self._submission.channel_username = self._subreddit.channel_username(default='')

        if not skip_sender_type_detection and not self._subreddit.force_text:
            try:
                self._detect_sender_type(sender_kwargs)
            except Exception as e:
                # this function might raise an error during the initialization of a class. For example, the Imgur
                # sender's __init__ method makes an API request that might raise an exception (eg. 404,
                # see submission "mifqyq" for an example)
                self.log.error("error while initializing the sender type: %s", str(e), exc_info=True)
        else:
            self.log.info(
                'skipping sender type detection (skip_sender_type_detection: %s, self._subreddit.force_text: %s)',
                skip_sender_type_detection,
                self._subreddit.force_text
            )

        # u.print_submission(self._s)

        self.gen_submission_dict()
        self.save_flair()

    def _detect_sender_type(self, sender_kwargs):
        if ImageHandler.test(self._submission):
            self.log.debug('url is a jpg/png')
            self.submission_handler = ImageHandler(**sender_kwargs)
        elif GifHandler.test(self._submission):
            self.log.debug('url is an imgur direct url to gif/gifv')
            self.submission_handler = GifHandler(**sender_kwargs)
        elif ImgurGalleryHandler.test(self._submission):
            self.log.debug('url is an imgur gallery')
            self.submission_handler = ImgurGalleryHandler(**sender_kwargs)
        elif VideoHandler.test(self._submission):
            self.log.debug('url is an mp4')
            self.submission_handler = VideoHandler(**sender_kwargs)
        elif GalleryImagesHandler.test(self._submission):
            self.log.debug('submission has submission.gallery_data')
            self.submission_handler = GalleryImagesHandler(**sender_kwargs)
        elif RedditGifHandler.test(self._submission):
            self.log.debug('url is an i.redd.it gif')
            self.submission_handler = RedditGifHandler(**sender_kwargs)
        elif GfycatHandler.test(self._submission):
            self.log.debug('url is a gfycat')
            self.submission_handler = GfycatHandler(**sender_kwargs)
        elif YouTubeHandler.test(self._submission, self._subreddit):
            self.log.debug('url is a youtube url (and the subreddit config says to download youtube videos)')
            self.submission_handler = YouTubeHandler(**sender_kwargs)
        elif VRedditHandler.test(self._submission):
            self.log.debug('url is a vreddit')
            self.submission_handler = VRedditHandler(**sender_kwargs)
        # these two are at the end because the test performs a network request (imgur api)
        elif ImgurNonDirectUrlImageHandler.test(self._submission):
            self.log.debug('url is an imgur non-direct url (image)')
            self.submission_handler = ImgurNonDirectUrlImageHandler(**sender_kwargs)
        elif ImgurNonDirectUrlVideoHandler.test(self._submission):
            self.log.debug('url is an imgur non-direct url (video/gif/gifv)')
            self.submission_handler = ImgurNonDirectUrlVideoHandler(**sender_kwargs)

    @property
    def submission(self):
        return self._submission

    @property
    def submission_dict(self):
        return self._submission_dict

    @property
    def subreddit(self):
        return self._subreddit

    @property
    def uploaded_bytes(self):
        return self._uploaded_bytes

    @property
    def template_keys(self):
        return_list = list()
        for key in self._submission_dict.keys():
            if not key.startswith('_') and isinstance(self._submission_dict[key], (datetime.datetime, str, int)):
                return_list.append(key)

        return return_list

    def __getitem__(self, item):
        return self._submission_dict[item]

    def gen_submission_dict(self):
        self._submission_dict = dict()

        for key in dir(self._submission):
            if key.startswith('_'):
                continue

            val = getattr(self._submission, key)
            # try to stringify val, otherwise continue
            try:
                str(val)
            except ValueError:
                continue

            self._submission_dict[key] = val
            if key in KEY_MAPPER_DICT:
                # replace the key in the dict of the mapping object edits that value
                self._submission_dict[key] = KEY_MAPPER_DICT[key](val)

        for key in dir(self._subreddit):
            if key in ('channel', 'style'):
                continue

            if key.startswith('_') or key in ('DoesNotExist',):
                continue

            val = getattr(self._subreddit, key)
            # try to stringify val, otherwise continue
            try:
                str(val)  # no need to convert to string, we just have to try to
            except ValueError:
                continue

            self._submission_dict[key] = val

        # noinspection PyTypeChecker
        self._submission_dict = OrderedDict(sorted(self._submission_dict.items()))

    def _get_filled_template(self, base_text: [None, str], accept_none_base_text=True):
        """Fill the passed text with the submission's dict values.
        accept_none_base_text=False allows to raise an error if the base text is None. Otherwise, by default,
        if the base text is None, the function will return None"""

        if base_text is None and not accept_none_base_text:
            raise ValueError('template filling: base text is None')
        elif base_text is None and accept_none_base_text:
            return None

        return base_text.format(**self._submission_dict)

    def _generate_reply_markup(self):
        reply_markup = None
        if self._subreddit.style.url_button and self._subreddit.style.comments_button:
            reply_markup = InlineKeyboard.post_buttons_with_labels(
                url_button_url=self._submission.url,
                url_button_label=self._get_filled_template(self._subreddit.style.url_button_template),
                comments_button_url=self._submission.comments_url,
                comments_button_label=self._get_filled_template(self._subreddit.style.comments_button_template),
            )
        elif self._subreddit.style.url_button and not self._subreddit.style.comments_button:
            reply_markup = InlineKeyboard.post_buttons_with_labels(
                url_button_url=self._submission.url,
                url_button_label=self._get_filled_template(self._subreddit.style.url_button_template)
            )
        elif not self._subreddit.style.url_button and self._subreddit.style.comments_button:
            reply_markup = InlineKeyboard.post_buttons_with_labels(
                comments_button_url=self._submission.comments_url,
                comments_button_label=self._get_filled_template(self._subreddit.style.comments_button_template),
            )

        return reply_markup

    def _get_template(self, is_caption=False):
        if self._subreddit.template_override:
            # always use the override if it's set
            template = self._subreddit.template_override
        elif self._submission.is_xpost:
            # if the submission is an xpost, use the template we would use with submissions containing an url (so the
            # post will have a direct reference to the xposted thread)
            template = self._subreddit.style.template
        elif self.submission_handler.EXTERNAL_CONTENT and self._subreddit.respect_external_content_flag:
            # if we are sending a type of media that is flagged as EXTERNAL_CONTENT, and the subreddit is set to respect
            # this flag, then we use the template for url submissions, so it will include the submission url to
            # the external service (eg. YouTube/Twitter)
            template = self._subreddit.style.template
        elif is_caption:
            if self._subreddit.style.template_caption:
                # if template_caption is set, use it right away
                template = self._subreddit.style.template_caption
            elif self._subreddit.style.template_no_url_for_captions and self._subreddit.style.template_no_url:
                # if template_caption is NOT set, and template_no_url_for_captions is true, use template_no_url as fallback
                template = self._subreddit.style.template_no_url
            else:
                # ...otherwise, use the normal template as fallback
                template = self._subreddit.style.template
        elif not self._submission.textual or not self._subreddit.style.template_no_url:
            # if the submission has an url, or there is no template for textual threads (template_no_url), use the
            # template saved in the database
            template = self._subreddit.style.template
        else:
            # else (template_no_url is set and the submission is a textaul post), use template_no_url
            template = self._subreddit.style.template_no_url

        if not template:
            # if there is no correct template set in the db, use the default one
            self.log.info('no template: using the default one')
            template = DEFAULT_TEMPLATE

        return template

    def post(self, chat_id=None):
        if chat_id:
            self.log.info('overriding target chat id (%d) with %d', self.submission_handler.chat_id, chat_id)
            self.submission_handler.chat_id = chat_id
            self.submission_handler_text.chat_id = chat_id

        # generate two texts: one to be used in case we will send the media as caption,
        # the other one for when we send the media as text (or if sending as media fails)
        text = self._get_filled_template(self._get_template())
        caption = self._get_filled_template(self._get_template(is_caption=True))

        # self.log.info('post text: %s', text)

        reply_markup = self._generate_reply_markup()

        if not isinstance(self.submission_handler, TextHandler) and not self._subreddit.force_text:
            self.log.info('post is a media, sending it as media...')
            try:
                self._sent_messages = self.submission_handler.post(caption, reply_markup=reply_markup)
                self._sum_uploaded_bytes(self._sent_messages)

                return self._sent_messages
            except Exception as e:
                self.log.error('exeption during the sending of a media, sending as text. Error: %s', str(e),
                               exc_info=True)
        else:
            self.log.info('post is NOT a media (or sending medias is disabled for the sub), sending it as text')

        self.log.info('posting a text...')
        self._sent_messages = self.submission_handler_text.post(text, reply_markup=reply_markup)

        return self._sent_messages

    def _sum_uploaded_bytes(self, sent_message):
        uploaded_bytes = u.media_size(sent_message) or 0
        # logger.debug('registering we sent %d bytes (%s)', uploaded_bytes, u.human_readable_size(uploaded_bytes))

        self._uploaded_bytes += uploaded_bytes

    def save_flair(self):
        if self._submission.ascii_flair == DEFAULT_FLAIR:
            return

        return flairs.save_flair(self._subreddit.name, self._submission.ascii_flair)

    def register_post(self, test=False):
        if test:
            self.log.info('not creating Post row: %s is a testing subreddit', self._subreddit.r_name_with_id)
            return

        sent_message_json = None
        if isinstance(self._sent_messages, list):
            message_id = self._sent_messages[0].message_id
            if isinstance(self._sent_messages[0], PtbMessage):
                sent_message_json = json.dumps([m.to_dict() for m in self._sent_messages])
            elif isinstance(self._sent_messages[0], PyroMessage):
                sent_message_json = json.dumps([str(m) for m in self._sent_messages])
        elif isinstance(self._sent_messages, PtbMessage):
            message_id = self._sent_messages.message_id
            sent_message_json = self._sent_messages.to_json()
        elif isinstance(self._sent_messages, PyroMessage):
            message_id = self._sent_messages.message_id
            sent_message_json = str(self._sent_messages)
        else:
            message_id = self._sent_messages.message_id

        self.log.info('creating Post row...')
        with db.atomic():
            Post.create(
                submission_id=self._submission.id,
                subreddit=self._subreddit,
                channel=self._subreddit.channel,
                message_id=message_id if self._sent_messages else None,
                posted_at=u.now() if self._sent_messages else None,
                uploaded_bytes=self._uploaded_bytes,
                sent_message=sent_message_json
            )

    def test_filters(self):
        print(self._submission.author_username_lower, self._subreddit.get_users_blacklist())
        if self._subreddit.ignore_stickied and self._submission.stickied:
            self.log.info('tests failed: sticked submission')
            return False
        elif self._subreddit.medias_only and not self._submission.media_type:
            self.log.info('tests failed: submission is a text and we only want media posts')
            return False
        elif self._subreddit.min_score and isinstance(self._subreddit.min_score, int) and self._subreddit.min_score > self._submission.score:
            self.log.info('tests failed: not enough upvotes (%d/%d)', self._submission.score, self._subreddit.min_score)
            return False
        elif self._subreddit.allow_nsfw is not None and self._subreddit.allow_nsfw == False and self._submission.over_18:
            self.log.info('tests failed: submission is NSFW')
            return False
        elif self._subreddit.hide_spoilers and self._submission.spoiler == True:
            self.log.info('tests failed: submission is a spoiler')
            return False
        elif self._subreddit.ignore_flairless and not self._submission.flair_normalized:
            self.log.info('tests failed: submission does not have a flair')
            return False
        elif self._subreddit.min_upvote_perc and self._submission.upvote_perc < self._subreddit.min_upvote_perc:
            self.log.info(
                'tests failed: submission\'s upvote ratio is not good enough (db: %d, submission: %d)',
                self._subreddit.min_upvote_perc,
                self._submission.upvote_perc
            )
            return False
        elif self._subreddit.users_blacklist and self._submission.author_username_lower in self._subreddit.get_users_blacklist():
            self.log.info('tests failed: u/%s is blacklisted in this subreddit', self._submission.author_username_lower)
            return False
        elif self._subreddit.ignore_if_newer_than \
                and isinstance(self._subreddit.ignore_if_newer_than, int) \
                and self._submission.elapsed_minutes < self._subreddit.ignore_if_newer_than:
            self.log.info(
                'tests failed: too new (submitted: %s, elapsed: %s, ignore_if_newer_than: %d)',
                self._submission.created_utc_formatted,
                u.pretty_minutes(self._submission.elapsed_minutes),
                self._subreddit.ignore_if_newer_than
            )
            return False
        elif self._subreddit.ignore_if_older_than \
                and isinstance(self._subreddit.ignore_if_older_than, int) \
                and self._submission.elapsed_minutes > self._subreddit.ignore_if_older_than:
            self.log.info(
                'tests failed: too old (submitted: %s, elapsed: %s, ignore_if_older_than: %d)',
                self._submission.created_utc_formatted,
                u.pretty_minutes(self._submission.elapsed_minutes),
                self._subreddit.ignore_if_older_than
            )
            return False
        else:
            return True

    def write_temp_submission_dict(self):
        text = pformat(self.submission_dict)
        file_path = os.path.join('downloads', '{}.temp.txt'.format(self._submission.id))

        with open(file_path, 'w+') as f:
            f.write(text)

        return file_path
