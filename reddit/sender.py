import json
import logging
import datetime
import os
import re
from collections import OrderedDict
from pprint import pformat
from urllib.parse import urlparse

from telegram import Bot
from telegram import Message as PtbMessage
from pyrogram import Message as PyroMessage

from database import db
from .submissions import Text
from .submissions import GalleryImages
from .submissions import Image
from .submissions import VReddit
from .submissions import Video
from .submissions import Gfycat
from .submissions import Gif
from .submissions import ImgurGallery, ImgurNonDirectUrlImage, ImgurNonDirectUrlVideo
from .submissions import RedditGif
from .submissions import YouTube
from bot.markups import InlineKeyboard
from database.models import Post
from database.models import Subreddit
from const import DEFAULT_TEMPLATE
from utilities import u
from config import config

logger = logging.getLogger('sp')

KEY_MAPPER_DICT = dict(
    created_utc=lambda timestamp: datetime.datetime.utcfromtimestamp(timestamp),
    created=lambda timestamp: datetime.datetime.fromtimestamp(timestamp)
)

HIDDEN_CHAR = u'\u200B'

DEFAULT_THUMBNAILS = {
    # https://old.reddit.com/r/redditdev/comments/2wwuje/what_does_it_mean_when_the_thumbnail_field_has/
    'self': 'https://www.reddit.com/static/self_default2.png',
    'nsfw': 'https://www.reddit.com/static/nsfw2.png',
    'default': 'https://www.reddit.com/static/noimage.png',
    'spoiler': 'https://www.reddit.com/static/self_default2.png'  # this is actually not the correct icon
}


class Sender:
    __slots__ = ['_bot', '_subreddit', '_s', '_sent_message', '_uploaded_bytes', '_chat_id', '_submission_dict', 'log', 'sender']
    
    def __init__(self, bot, subreddit, submission):
        self._bot: Bot = bot
        self._s = submission
        self._subreddit: Subreddit = subreddit
        if hasattr(subreddit, 'logger'):
            self.log = subreddit.logger
        else:
            self.log = logger

        self._sent_message = None
        self._uploaded_bytes = 0
        sender_kwargs = dict(submission=self._s, subreddit=self._subreddit, bot=self._bot)
        self.sender = Text(**sender_kwargs)

        self._s.is_image = False
        self._s.flair_with_space = ''  # i don't remember why this is a thing
        self._s.flair_normalized = ''  # ascii flair
        self._s.ascii_flair = 'no_flair'  # ascii flair, will be "no_flair" when submission doesn't have a falir
        self._s.nsfw = self._s.over_18
        self._s.sorting = self._subreddit.sorting or 'hot'
        self._s.comments_url = 'https://www.reddit.com{}'.format(self._s.permalink)
        self._s.hidden_char = HIDDEN_CHAR  # we might need it for some templates
        self._s.hidden_url_comments = '<a href="{}">{}</a>'.format(self._s.comments_url, HIDDEN_CHAR)
        self._s.hidden_url = '<a href="{}">{}</a>'.format(self._s.url, HIDDEN_CHAR)
        self._s.score_dotted = u.dotted(self._s.score or 0)
        self._s.num_comments_dotted = u.dotted(self._s.num_comments or 0)
        self._s.domain_parsed = urlparse(self._s.url).netloc
        self._s.title_escaped = u.escape(self._s.title)
        self._s.text = ''
        self._s.text_32 = ''
        self._s.text_160 = ''
        self._s.text_200 = ''
        self._s.text_256 = ''
        self._s.video_size = (None, None)
        self._s.video_duration = 0
        self._s.upvote_perc = int(self._s.upvote_ratio * 100)
        self._submission_dict = dict()

        # for crossposts: only the reference to the original post contains the 'media' attribute of the submission.
        # We can get the parent submission of the crosspost from `submission.crosspost_parent_list[0]`
        # and then we can add it to the crossposted submission
        self._s.is_xpost = False
        self._s.xpost_from = ''
        self._s.xpost_from_string = ''
        if hasattr(self._s, 'crosspost_parent') and len(self._s.crosspost_parent_list) > 0:
            self._s.is_xpost = True
            # sometimes submissions has the 'crosspost_parent' but there's no item in 'crosspost_parent_list'
            self.log.info('note: submission is a crosspost of %s (overriding media attributes...)', self._s.crosspost_parent)
            self._s.xpost_from = self._s.crosspost_parent_list[0].get('subreddit', '')
            self._s.media = self._s.crosspost_parent_list[0].get('media', None)
            self._s.is_video = self._s.crosspost_parent_list[0].get('is_video', False)
            self._s.thumbnail = self._s.crosspost_parent_list[0].get('thumbnail', None)
            self._s.media_metadata = self._s.crosspost_parent_list[0].get('media_metadata', None)

        if self._s.thumbnail and self._s.thumbnail.lower() in DEFAULT_THUMBNAILS:
            # https://old.reddit.com/r/redditdev/comments/2wwuje/what_does_it_mean_when_the_thumbnail_field_has/
            self._s.thumbnail = DEFAULT_THUMBNAILS[self._s.thumbnail.lower()]
        elif not self._s.thumbnail:
            self._s.thumbnail = 'https://www.reddit.com/static/noimage.png'

        if self._s.link_flair_text is not None:
            self._s.flair_with_space = '[{}] '.format(self._s.link_flair_text)
            ascii_flair = u.to_ascii(str(self._s.link_flair_text), replace_spaces=True, lowercase=True)
            self._s.flair_normalized = ascii_flair
            self._s.ascii_flair = ascii_flair

        # if the post is a textual post, it will contain a "thread" inline url. Otherwise it will contain the "url"
        # and "comments" inline urls
        if self._s.comments_url == self._s.url:
            self._s.textual = True
            self._s.thread_or_urls = '<a href="{}">thread</a>'.format(self._s.comments_url)
            self._s.force_disable_link_preview = True
        else:
            self._s.textual = False
            self._s.thread_or_urls = '<a href="{}">url</a> • <a href="{}">comments</a>'.format(
                self._s.url,
                self._s.comments_url
            )
            self._s.force_disable_link_preview = False

        if self._s.selftext:
            text_len = len(self._s.selftext)
            self._s.text = self._s.selftext
            self._s.text_32 = '{}{}'.format(self._s.selftext[:32], '' if text_len <= 32 else ' [...]')
            self._s.text_160 = '{}{}'.format(self._s.selftext[:160], '' if text_len <= 160 else ' [...]')
            self._s.text_200 = '{}{}'.format(self._s.selftext[:200], '' if text_len <= 200 else ' [...]')
            self._s.text_256 = '{}{}'.format(self._s.selftext[:256], '' if text_len <= 256 else ' [...]')

        created_utc_dt = datetime.datetime.utcfromtimestamp(self._s.created_utc)
        self._s.created_utc_formatted = created_utc_dt.strftime('%d/%m/%Y, %H:%M')

        if self._subreddit.style.comments_button \
            or (self._subreddit.enabled and self._subreddit.style.template and '{num_comments}' in self._subreddit.style.template) \
            or (self._subreddit.enabled_resume and self._subreddit.style.template_resume and '{num_comments}' in self._subreddit.style.template_resume):
            # calling a subreddit's num_comments property probably executes an API request. Make it
            # an int if we'll need it
            self._s.num_comments = int(self._s.num_comments)

        self._s.elapsed_seconds = (u.now() - created_utc_dt).total_seconds()
        self._s.elapsed_minutes = int(round(self._s.elapsed_seconds / 60))
        self._s.elapsed_hours = int(round(self._s.elapsed_minutes / 60))

        # "n hours ago" if hours > 0, else "n minutes ago"
        self._s.elapsed_smart = u.elapsed_time_smart(self._s.elapsed_seconds)
        self._s.elapsed_smart_compact = u.elapsed_smart_compact(self._s.elapsed_seconds)

        self._s.index_channel_link = 'https://t.me/{}'.format(config.telegram.index) if config.telegram.get('index', None) else None
        self._s.index_channel_username = '@{}'.format(config.telegram.index) if config.telegram.get('index', None) else None
        self._s.channel_invite_link = self._subreddit.channel_link
        self._s.channel_username = self._subreddit.channel_username(default='')

        if Image.test(self._s):
            self.log.debug('url is a jpg/png')
            self.sender = Image(**sender_kwargs)
        elif Gif.test(self._s):
            self.log.debug('url is an imgur direct url to gif/gifv')
            self.sender = Gif(**sender_kwargs)
        elif ImgurGallery.test(self._s):
            self.log.debug('url is an imgur gallery')
            self.sender = ImgurGallery(**sender_kwargs)
        elif Video.test(self._s):
            self.log.debug('url is an mp4')
            self.sender = Video(**sender_kwargs)
        elif GalleryImages.test(self._s):
            self.log.debug('submission has submission.gallery_data')
            self.sender = GalleryImages(**sender_kwargs)
        elif RedditGif.test(self._s):
            self.log.debug('url is an i.redd.it gif')
            self.sender = RedditGif(**sender_kwargs)
        elif Gfycat.test(self._s):
            self.log.debug('url is a gfycat')
            self.sender = Gfycat(**sender_kwargs)
        elif YouTube.test(self._s, self._subreddit):
            self.log.debug('url is a youtube url (and the subreddit config says to download youtube videos)')
            self.sender = YouTube(**sender_kwargs)
        elif VReddit.test(self._s):
            self.log.debug('url is a vreddit')
            self.sender = VReddit(**sender_kwargs)
        # these two are at the end because the test performs a network request (imgur api)
        elif ImgurNonDirectUrlImage.test(self._s):
            self.log.debug('url is an imgur non-direct url (image)')
            self.sender = ImgurNonDirectUrlImage(**sender_kwargs)
        elif ImgurNonDirectUrlVideo.test(self._s):
            self.log.debug('url is an imgur non-direct url (video/gif/gifv)')
            self.sender = ImgurNonDirectUrlVideo(**sender_kwargs)

        # u.print_submission(self._s)

        self.gen_submission_dict()

    @property
    def submission(self):
        return self._s

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

        for key in dir(self._s):
            if key.startswith('_'):
                continue
                
            val = getattr(self._s, key)
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
                url_button_url=self._s.url,
                url_button_label=self._get_filled_template(self._subreddit.style.url_button_template),
                comments_button_url=self._s.comments_url,
                comments_button_label=self._get_filled_template(self._subreddit.style.comments_button_template),
            )
        elif self._subreddit.style.url_button and not self._subreddit.style.comments_button:
            reply_markup = InlineKeyboard.post_buttons_with_labels(
                url_button_url=self._s.url,
                url_button_label=self._get_filled_template(self._subreddit.style.url_button_template)
            )
        elif not self._subreddit.style.url_button and self._subreddit.style.comments_button:
            reply_markup = InlineKeyboard.post_buttons_with_labels(
                comments_button_url=self._s.comments_url,
                comments_button_label=self._get_filled_template(self._subreddit.style.comments_button_template),
            )

        return reply_markup

    def _get_template(self, is_caption=False):
        if self._subreddit.template_override:
            # always use the override if it's set
            template = self._subreddit.template_override
        elif self._s.is_xpost:
            # if the submission is an xpost, use the template we would use with submissions containing an url (so the
            # post will have a direct reference to the xposted thread)
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
        elif not self._s.textual or not self._subreddit.style.template_no_url:
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
            self.log.info('overriding target chat id (%d) with %d', self.sender.chat_id, chat_id)
            self.sender.chat_id = chat_id

        # generate two texts: one to be used in case we will send the media as caption,
        # the other one for when we send the media as text (or if sending as media fails)
        text = self._get_filled_template(self._get_template())
        caption = self._get_filled_template(self._get_template(is_caption=True))

        # self.log.info('post text: %s', text)

        reply_markup = self._generate_reply_markup()
        
        if not isinstance(self.sender, Text) and not self._subreddit.force_text:
            self.log.info('post is a media, sending it as media...')
            try:
                self._sent_message = self.sender.post(caption, reply_markup=reply_markup)

                return self._sent_message
            except Exception as e:
                self.log.error('exeption during the sending of a media, sending as text. Error: %s', str(e), exc_info=False)
        else:
            self.log.info('post is NOT a media (or sending medias is disabled for the sub), sending it as text')
        
        self.log.info('posting a text...')
        self._sent_message = self.sender.post(text, reply_markup=reply_markup)

        return self._sent_message

    def _sum_uploaded_bytes(self, sent_message):
        uploaded_bytes = u.media_size(sent_message) or 0
        # logger.debug('registering we sent %d bytes (%s)', uploaded_bytes, u.human_readable_size(uploaded_bytes))

        self._uploaded_bytes += uploaded_bytes

    def register_post(self, test=False):
        if test:
            self.log.info('not creating Post row: %s is a testing subreddit', self._subreddit.r_name_with_id)
            return

        if isinstance(self._sent_message, list):
            message_id = self._sent_message[0].message_id
            if isinstance(self._sent_message[0], PtbMessage):
                sent_message_json = json.dumps([m.to_dict() for m in self._sent_message])
            elif isinstance(self._sent_message[0], PyroMessage):
                sent_message_json = json.dumps([str(m) for m in self._sent_message])
        elif isinstance(self._sent_message, PtbMessage):
            message_id = self._sent_message.message_id
            sent_message_json = self._sent_message.to_json()
        elif isinstance(self._sent_message, PyroMessage):
            message_id = self._sent_message.message_id
            sent_message_json = str(self._sent_message)
        else:
            message_id = self._sent_message.message_id
            sent_message_json = None

        self.log.info('creating Post row...')
        with db.atomic():
            Post.create(
                submission_id=self._s.id,
                subreddit=self._subreddit,
                channel=self._subreddit.channel,
                message_id=message_id if self._sent_message else None,
                posted_at=u.now() if self._sent_message else None,
                uploaded_bytes=self._uploaded_bytes,
                sent_message=sent_message_json
            )
    
    def test_filters(self):
        if self._subreddit.ignore_stickied and self._s.stickied:
            self.log.info('tests failed: sticked submission')
            return False
        elif self._subreddit.medias_only and not self._s.media_type:
            self.log.info('tests failed: submission is a text and we only want media posts')
            return False
        elif self._subreddit.min_score and isinstance(self._subreddit.min_score, int) and self._subreddit.min_score > self._s.score:
            self.log.info('tests failed: not enough upvotes (%d/%d)', self._s.score, self._subreddit.min_score)
            return False
        elif self._subreddit.allow_nsfw is not None and self._subreddit.allow_nsfw == False and self._s.over_18:
            self.log.info('tests failed: submission is NSFW')
            return False
        elif self._subreddit.hide_spoilers and self._s.spoiler == True:
            self.log.info('tests failed: submission is a spoiler')
            return False
        elif self._subreddit.ignore_flairless and not self._s.flair_normalized:
            self.log.info('tests failed: submission does not have a flair')
            return False
        elif self._subreddit.min_upvote_perc and self._s.upvote_perc < self._subreddit.min_upvote_perc:
            self.log.info(
                'tests failed: submission\'s upvote ratio is not good enough (db: %d, submission: %d)',
                self._subreddit.min_upvote_perc,
                self._s.upvote_perc
            )
            return False
        elif self._subreddit.ignore_if_newer_than \
                and isinstance(self._subreddit.ignore_if_newer_than, int) \
                and self._s.elapsed_minutes < self._subreddit.ignore_if_newer_than:
            self.log.info(
                'tests failed: too new (submitted: %s, elapsed: %s, ignore_if_newer_than: %d)',
                self._s.created_utc_formatted,
                u.pretty_minutes(self._s.elapsed_minutes),
                self._subreddit.ignore_if_newer_than
            )
            return False
        else:
            return True
    
    def write_temp_submission_dict(self):
        text = pformat(self.submission_dict)
        file_path = os.path.join('downloads', '{}.temp.txt'.format(self._s.id))
    
        with open(file_path, 'w+') as f:
            f.write(text)
            
        return file_path
