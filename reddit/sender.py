import os
import logging
import datetime
import re
from urllib.parse import urlparse

from telegram import ParseMode
from telegram.error import BadRequest
from telegram.error import TelegramError

from .downloaders import Imgur
from .downloaders import Downloader
from .downloaders import VReddit
from .downloaders import FileTooBig
from database.models import Post
from database.models import Ignored
from const import DEFAULT_TEMPLATE
from utilities import u
from config import config

logger = logging.getLogger(__name__)

imgur = Imgur(config.imgur.id, config.imgur.secret)

KEY_MAPPER_DICT = dict(
    created_utc=lambda timestamp: datetime.datetime.utcfromtimestamp(timestamp),
    created=lambda timestamp: datetime.datetime.fromtimestamp(timestamp)
)


class ImagesWebsites:
    IMGUR = 'imgur'


class MediaType:
    NONE = None
    IMAGE = 'image'
    GIF = 'gif'
    VIDEO = 'video'
    VREDDIT = 'vreddit'


class Sender(dict):
    def __init__(self, bot, subreddit, submission):
        super(Sender, self).__init__()
        self._bot = bot
        self._s = submission
        self._subreddit = subreddit

        self._sent_message = None

        self._s.is_image = False
        self._s.media_type = MediaType.NONE
        self._s.flair_with_space = ''
        self._s.nsfw = self._s.over_18
        self._s.sorting = self._subreddit.sorting or 'hot'
        self._s.comments_url = 'https://www.reddit.com{}'.format(self._s.permalink)
        self._s.score_dotted = u.dotted(self._s.score or 0)
        self._s.num_comments_dotted = u.dotted(self._s.num_comments or 0)
        self._s.domain_parsed = urlparse(self._s.url).netloc
        self._s.text = None
        self._s.text_32 = None
        self._s.text_160 = None
        self._s.text_200 = None
        self._s.text_256 = None
        self._s.video_size = (None, None)
        self._s.video_duration = 0
        
        # this whole shit should have its own method
        if self._s.url.endswith(('.jpg', '.png')):
            logger.debug('url is a jpg/png: submission is an image')
            self._s.media_type = MediaType.IMAGE
            self._s.media_url = self._s.url
        if self._s.url.endswith('.gifv'):
            logger.debug('url is a gifv: submission is an GIF')
            self._s.media_type = MediaType.GIF
            self._s.media_url = self._s.url
        elif re.search(r'imgur\.com/[a-zA-Z1-9]+$', self._s.url, re.I):
            # check if the url is an url to an Imgur image even if it doesn't end with jpg/png
            imgur_direct_url = imgur.get_url(re.search(r'imgur\.com/([a-zA-Z1-9]+)$', self._s.url, re.I).group(1))
            logger.debug('imgur direct url: %s', imgur_direct_url)
            # also make sure the url is of an image
            if imgur_direct_url.endswith(('.jpg', '.png')):
                logger.debug('url is an Imgur non-direct url to an image: submission is an image')
                self._s.media_type = MediaType.IMAGE
                self._s.media_url = imgur_direct_url
            elif imgur_direct_url.endswith('.gifv'):
                logger.debug('url is an Imgur non-direct url to a gifv: submission is a GIF')
                self._s.media_type = MediaType.GIF
                logger.debug('replacing ".gifv" with ".mp4"')
                self._s.media_url = imgur_direct_url.replace('.gifv', '.mp4')
        elif self._s.url.endswith('.mp4'):
            logger.debug('url is an mp4: submission is a video')
            self._s.media_type = MediaType.VIDEO
            self._s.media_url = self._s.url
        elif self._s.is_video and 'reddit_video' in self._s.media:
            logger.debug('url is a vreddit')
            self._s.media_type = MediaType.VREDDIT
            self._s.media_url = self._s.media['reddit_video']['fallback_url']
            self._s.video_size = (
                self._s.media['reddit_video']['height'],
                self._s.media['reddit_video']['width']
            )
            self._s.video_duration = self._s.media['reddit_video']['duration']

        if self._s.link_flair_text is not None:
            self._s.flair_with_space = '[{}] '.format(self._s.link_flair_text)

        # if the post is a textual post, it will contain a "thread" inline url. Otherwise it will contain the "url"
        # and "comments" inline urls
        if self._s.comments_url == self._s.url:
            self._s.textual = True
            self._s.thread_or_urls = '<a href="{}">thread</a>'.format(self._s.comments_url)
        else:
            self._s.textual = False
            self._s.thread_or_urls = '<a href="{}">url</a> • <a href="{}">comments</a>'.format(
                self._s.url,
                self._s.comments_url
            )

        if self._s.selftext:
            self._s.text = self._s.selftext
            self._s.text_32 = self._s.selftext[:32]
            self._s.text_160 = self._s.selftext[:120]
            self._s.text_200 = self._s.selftext[:200]
            self._s.text_256 = self._s.selftext[:256]

        created_utc_dt = datetime.datetime.utcfromtimestamp(self._s.created_utc)

        self._s.title_escaped = u.escape(self._s.title)
        self._s.created_utc_formatted = created_utc_dt.strftime('%d/%m/%Y, %H:%M')

        self._s.elapsed_seconds = (u.now() - created_utc_dt).seconds
        self._s.elapsed_minutes = self._s.elapsed_seconds / 60
        self._s.elapsed_hours = self._s.elapsed_minutes / 60

        # "n hours ago" if hours > 0, else "n minutes ago"
        self._s.elapsed_smart = u.elapsed_time_smart(self._s.elapsed_seconds)

        self._submission_dict = dict()

        for key in dir(self._s):
            val = getattr(submission, key)
            self._submission_dict[key] = val
            if KEY_MAPPER_DICT.get(key, None):
                # replace the key in the dict of the mapping object edits that value
                self._submission_dict[key] = KEY_MAPPER_DICT[key](val)

    @property
    def submission(self):
        return self._s

    @property
    def submission_dict(self):
        return self._submission_dict

    @property
    def template_keys(self):
        return [key for key in self._submission_dict.keys() if not key.startswith('_') and isinstance(self._submission_dict[key], (datetime.datetime, str, int))]

    def __getitem__(self, item):
        return self._submission_dict[item]

    def post(self):
        template = self._subreddit.template
        if not template:
            logger.info('no template: using the default one')
            template = DEFAULT_TEMPLATE

        text = template.format(**self._submission_dict)
        # logger.info('post text: %s', text)
        
        if self._s.media_type and self._subreddit.send_medias:
            logger.info('post is a media, sending it as media...')
            try:
                if self._s.media_type == MediaType.IMAGE:
                    logger.info('post is an image: using _send_image()')
                    self._sent_message = self._send_image(self._s.media_url, text)
                elif self._s.media_type == MediaType.VREDDIT:
                    logger.info('post is a vreddit: using _send_vreddit()')
                    self._sent_message = self._send_vreddit(self._s.media_url, text)
                elif self._s.media_type == MediaType.VIDEO:
                    logger.info('post is a video: using _send_video()')
                    self._sent_message = self._send_video(self._s.media_url, text)
                elif self._s.media_type == MediaType.GIF:
                    logger.info('post is a gif: using _send_gif()')
                    self._sent_message = self._send_gif(self._s.media_url, text)
                
                return self._sent_message
            except Exception as e:
                logger.error('exeption during the sending of a media, sending as text', exc_info=True)
        
        logger.info('submission is textual -or- send_medias is false -or- sending media failed: posting a text...')
        self._sent_message = self._send_text(text)

        return self._sent_message

    def _send_text(self, text):
        return self._bot.send_message(
            self._subreddit.channel.channel_id,
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=not self._subreddit.webpage_preview
        )

    def _send_image(self, image_url, caption):
        self._sent_message = self._bot.send_photo(
            self._subreddit.channel.channel_id,
            image_url,
            caption=caption,
            parse_mode=ParseMode.HTML,
            timeout=360
        )
        return self._sent_message

    def _send_vreddit(self, url, caption):
        vreddit = VReddit(url)
        file_path = vreddit.file_path
        try:
            logger.info('downloading video/audio and merging them...')
            file_path = vreddit.download_and_merge()
            logger.info('...merging ended')
        except FileTooBig:
            logger.info('video is too big to be sent (%s), removing file and sending text...', vreddit.size_readable)
            vreddit.remove()
            raise FileTooBig

        thumb_file, thumbnail_path = None, None
        if self._s.thumbnail:
            thumbnail_path = u.download_file_stream(self._s.thumbnail, os.path.join('downloads', 'thumb_{}.jpg'.format(self._s.id)))
            thumbnail_path = u.resize_thumbnail(thumbnail_path)
            thumb_file = open(thumbnail_path, 'rb')

        with open(file_path, 'rb') as f:
            logger.info('uploading video...')
            self._sent_message = self._bot.send_video(
                self._subreddit.channel.channel_id,
                f,
                caption=caption,
                parse_mode=ParseMode.HTML,
                thumb=thumb_file,
                height=self._s.video_size[0],
                width=self._s.video_size[1],
                duration=self._s.video_duration,
                supports_streaming=True,
                timeout=360
            )

        thumb_file.close()

        logger.info('removing downloaded files...')
        vreddit.remove()
        u.remove_file_safe(thumbnail_path)

        return self._sent_message

    def _send_video(self, url, caption, send_text_fallback=True):
        video = Downloader(url)
        try:
            logger.info('downloading video...')
            video.download()
            logger.info('...download ended')
        except FileTooBig:
            logger.info('video is too big to be sent (%s), removing file and sending text...', video.size_readable)
            video.remove()
            
            raise FileTooBig
        
        thumb_path = 'assets/video_thumb.png'  # generic thumbnail
        thumb_file = open(os.path.normpath(thumb_path), 'rb')
        
        logger.debug('opening and sending video...')
        with open(video.file_path, 'rb') as f:
            self._sent_message = self._bot.send_video(
                self._subreddit.channel.channel_id,
                f,
                caption=caption,
                thumb=thumb_file,
                height=None,
                width=None,
                duration=None,
                parse_mode=ParseMode.HTML,
                supports_streaming=True,
                timeout=360
            )
        logger.debug('...upload completed')

        thumb_file.close()
        logger.info('removing downloaded files...')
        video.remove()
        # DO NOT DELETE THE GENERIC THUMBNAIL FILE
        
        return self._sent_message
    
    def _send_gif(self, url, caption):
        return self._bot.send_animation(
            self._subreddit.channel.channel_id,
            url,
            caption=caption,
            parse_mode=ParseMode.HTML,
            timeout=360
        )
    
    def register_post(self):
        Post.create(
            submission_id=self._s.id,
            subreddit=self._subreddit,
            channel=self._subreddit.channel,
            message_id=self._sent_message.message_id if self._sent_message else None,
            posted_at=u.now() if self._sent_message else None
        )
    
    def register_ignored(self):
        Ignored.create(
            submission_id=self._s.id,
            subreddit=self._subreddit,
            ignored_at=u.now() if self._sent_message else None
        )
    
    def test_filters(self):
        if self._subreddit.ignore_stickied and self._s.stickied:
            logger.info('tests failed: sticked submission')
            return False
        elif self._subreddit.images_only and not self._s.media_type == MediaType.IMAGE:
            logger.info('tests failed: subreddit is not an image')
            return False
        elif self._subreddit.min_score and isinstance(self._subreddit.min_score, int) and self._subreddit.min_score > self._s.score:
            logger.info('tests failed: not enough upvotes (%d/%d)', self._s.score, self._subreddit.min_score)
            return False
        elif self._subreddit.allow_nsfw is not None and self._subreddit.allow_nsfw == False and self._s.over_18:
            logger.info('tests failed: submission is NSFW')
            return False
        elif self._subreddit.ignore_if_newer_than \
                and isinstance(self._subreddit.ignore_if_newer_than, datetime.datetime) \
                and ((u.now() - self._s.created_utc).seconds / 60) < self._subreddit.ignore_if_newer_than:
            logger.info('tests failed: too new (submitted: %s)', self._s.created_utc_formatted)
            return False
        else:
            return True
        



