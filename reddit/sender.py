import logging
import datetime
import os
import re
from collections import OrderedDict
import pprint
from urllib.parse import urlparse

from telegram import Bot
from telegram import ParseMode
from telegram.error import BadRequest
from telegram.error import TelegramError

from const import MaxSize
from .downloaders import Imgur
from .downloaders import Downloader
from .downloaders import VReddit
from.downloaders.vreddit import FfmpegTimeoutError
from .downloaders import Gfycat
from .downloaders import FileTooBig
from pyroutils import PyroClient
from database.models import Post
from database.models import Ignored
from const import DEFAULT_TEMPLATE
from utilities import u
from config import config

logger = logging.getLogger('sp')

imgur = Imgur(config.imgur.id, config.imgur.secret)
mtproto = PyroClient(
    'pyrogram_bot',
    bot_token=config.telegram.token,
    api_id=config.pyrogram.api_id,
    api_hash=config.pyrogram.api_hash,
    workers=config.pyrogram.workers,
    no_updates=True
)

KEY_MAPPER_DICT = dict(
    created_utc=lambda timestamp: datetime.datetime.utcfromtimestamp(timestamp),
    created=lambda timestamp: datetime.datetime.fromtimestamp(timestamp)
)

SINGLE_IMGUR_MEDIA_URL_REGEX = r'imgur\.com/([a-zA-Z0-9]+)$'


class ImagesWebsites:
    IMGUR = 'imgur'


class MediaType:
    NONE = None
    IMAGE = 'image'
    GIF = 'gif'
    VIDEO = 'video'
    VREDDIT = 'vreddit'
    GFYCAT = 'gfycat'


class Media:
    def __init__(self, media_type, url):
        self.type = media_type
        self.url = url


class VRedditMedia(Media):
    def __init__(self, is_gif, size, duration, *args, **kwargs):
        Media.__init__(self, *args, **kwargs)
        self.is_gif = is_gif
        self.size = size
        self.duration = duration


class Sender:
    __slots__ = ['_bot', '_subreddit', '_s', '_sent_message', '_chat_id', '_submission_dict']
    
    def __init__(self, bot, subreddit, submission):
        self._bot: Bot = bot
        self._s = submission
        self._subreddit = subreddit

        self._sent_message = None
        self._chat_id = self._subreddit.channel.channel_id

        self._s.is_image = False
        self._s.media_type = MediaType.NONE
        self._s.flair_with_space = ''
        self._s.flair_normalized = ''
        self._s.nsfw = self._s.over_18
        self._s.sorting = self._subreddit.sorting or 'hot'
        self._s.comments_url = 'https://www.reddit.com{}'.format(self._s.permalink)
        self._s.score_dotted = u.dotted(self._s.score or 0)
        self._s.num_comments_dotted = u.dotted(self._s.num_comments or 0)
        self._s.domain_parsed = urlparse(self._s.url).netloc
        self._s.title_escaped = u.escape(self._s.title)
        self._s.text = None
        self._s.text_32 = None
        self._s.text_160 = None
        self._s.text_200 = None
        self._s.text_256 = None
        self._s.video_size = (None, None)
        self._s.video_duration = 0
        self._submission_dict = dict()

        # for crossposts: only the reference to the original post contains the 'media' attribute of the submission.
        # We can get the parent submission of the crosspost from `submission.crosspost_parent_list[0]`
        # and then we can add it to the crossposted submission
        self._s.xpost_from = ''
        self._s.xpost_from_string = ''
        if hasattr(self._s, 'crosspost_parent'):
            logger.info('note: submission is a crosspost of %s', self._s.crosspost_parent)
            self._s.xpost_from = self._s.crosspost_parent_list[0].get('subreddit', '')
            self._s.xpost_from_string = 'xpost from /r/{}'.format(self._s.xpost_from)
            self._s.xpost_from_string_dotted = '• {}'.format(self._s.xpost_from_string)
            self._s.media = self._s.crosspost_parent_list[0].get('media', None)
            self._s.is_video = self._s.crosspost_parent_list[0].get('is_video', False)
            self._s.thumbnail = self._s.crosspost_parent_list[0].get('thumbnail', None)

        # this whole shit should have its own method
        if self._s.url.endswith(('.jpg', '.png')):
            logger.debug('url is a jpg/png: submission is an image')
            self._s.media_type = MediaType.IMAGE
            self._s.media_url = self._s.url
        elif self._s.url.endswith('.gifv'):
            logger.debug('url is a gifv: submission is an GIF')
            self._s.media_type = MediaType.GIF
            self._s.media_url = self._s.url.replace('.gifv', '.mp4')
        elif re.search(SINGLE_IMGUR_MEDIA_URL_REGEX, self._s.url, re.I):
            # check if the url is an url to an Imgur image even if it doesn't end with jpg/png
            imgur_direct_url = imgur.get_url(re.search(SINGLE_IMGUR_MEDIA_URL_REGEX, self._s.url, re.I).group(1))
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
                logger.debug('new media_url: %s', self._s.media_url)
            elif imgur_direct_url.endswith('.mp4'):
                self._s.media_type = MediaType.GIF
                self._s.media_url = imgur_direct_url
        elif self._s.url.endswith('.mp4'):
            logger.debug('url is an mp4: submission is a video')
            self._s.media_type = MediaType.VIDEO
            self._s.media_url = self._s.url
        elif self._s.domain == 'i.redd.it' and self._s.url.endswith('.gif'):
            logger.debug('url is an i.redd.it gif: treating the submission as a video')
            self._s.media_type = MediaType.VIDEO
            self._s.media_url = self._s.url
        elif 'gfycat.com' in self._s.domain_parsed:
            logger.debug('url is a gfycat')
            self._s.media_type = MediaType.GFYCAT
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
            self._s.is_gif = self._s.media['reddit_video'].get('is_gif', False)  # some v.reddit might not have audio

        if self._s.thumbnail:
            # https://old.reddit.com/r/redditdev/comments/2wwuje/what_does_it_mean_when_the_thumbnail_field_has/
            if self._s.thumbnail == 'self':
                self._s.thumbnail = 'https://www.reddit.com/static/self_default2.png'
            elif self._s.thumbnail == 'nsfw':
                self._s.thumbnail = 'https://www.reddit.com/static/nsfw2.png'
            else:
                self._s.thumbnail = 'https://www.reddit.com/static/noimage.png'

        if self._s.link_flair_text is not None:
            self._s.flair_with_space = '[{}] '.format(self._s.link_flair_text)
            ascii_flair = re.sub(r'[^a-z_0-9 ]+', '', str(self._s.link_flair_text), flags=re.I)
            self._s.flair_normalized = ascii_flair.replace(' ', '_').lower()

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
        self._s.created_utc_formatted = created_utc_dt.strftime('%d/%m/%Y, %H:%M')

        self._s.elapsed_seconds = (u.now() - created_utc_dt).total_seconds()
        self._s.elapsed_minutes = self._s.elapsed_seconds / 60
        self._s.elapsed_hours = self._s.elapsed_minutes / 60

        # "n hours ago" if hours > 0, else "n minutes ago"
        self._s.elapsed_smart = u.elapsed_time_smart(self._s.elapsed_seconds)

        self._s.index_channel_link = 'https://t.me/{}'.format(config.telegram.index) if config.telegram.get('index', None) else None
        self._s.index_channel_username = '@{}'.format(config.telegram.index) if config.telegram.get('index', None) else None
        self._s.channel_invite_link = self._subreddit.channel.invite_link or None

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
    def template_keys(self):
        return_list = list()
        for key in self._submission_dict.keys():
            if not key.startswith('_') and isinstance(self._submission_dict[key], (datetime.datetime, str, int)):
                return_list.append(key)
        
        return return_list
        
    def __getitem__(self, item):
        return self._submission_dict[item]

    @staticmethod
    def parse_media(url, media_dict):
        domain_parsed = urlparse(url).netloc

        if url.endswith(('.jpg', '.png')):
            logger.debug('url is a jpg/png: submission is an image')
            return Media(MediaType.IMAGE, url)
        elif url.endswith('.gifv'):
            logger.debug('url is a gifv: submission is an GIF')
            return Media(MediaType.GIF, url.replace('.gifv', '.mp4'))
        elif re.search(SINGLE_IMGUR_MEDIA_URL_REGEX, url, re.I):
            # check if the url is an url to an Imgur image even if it doesn't end with jpg/png
            imgur_direct_url = imgur.get_url(re.search(SINGLE_IMGUR_MEDIA_URL_REGEX, url, re.I).group(1))
            logger.debug('imgur direct url: %s', imgur_direct_url)
            # also make sure the url is of an image
            if imgur_direct_url.endswith(('.jpg', '.png')):
                logger.debug('url is an Imgur non-direct url to an image: submission is an image')
                return Media(MediaType.IMAGE, imgur_direct_url)
            elif imgur_direct_url.endswith('.gifv'):
                logger.debug('url is an Imgur non-direct url to a gifv: submission is a GIF')
                logger.debug('replacing ".gifv" with ".mp4"')
                mp4_url = imgur_direct_url.replace('.gifv', '.mp4')
                logger.debug('new media_url: %s', mp4_url)
                return Media(MediaType.GIF, mp4_url)
            elif imgur_direct_url.endswith('.mp4'):
                return Media(MediaType.GIF, imgur_direct_url)
        elif url.endswith('.mp4'):
            logger.debug('url is an mp4: submission is a video')
            return Media(MediaType.VIDEO, url)
        elif domain_parsed == 'i.redd.it' and url.endswith('.gif'):
            logger.debug('url is an i.redd.it gif: treating the submission as a video')
            return Media(MediaType.VIDEO, url)
        elif 'gfycat.com' in domain_parsed:
            logger.debug('url is a gfycat')
            return Media(MediaType.GFYCAT, url)
        elif 'reddit_video' in media_dict:
            logger.debug('url is a vreddit')
            media_url = media_dict['reddit_video']['fallback_url']
            video_size = (
                media_dict['reddit_video']['height'],
                media_dict['reddit_video']['width']
            )
            video_duration = media_dict['reddit_video']['duration']
            is_gif = media_dict['reddit_video'].get('is_gif', False)  # some v.reddit might not have audio

            return VRedditMedia(MediaType.VREDDIT, media_url, is_gif, video_size, video_duration)

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

    def post(self, chat_id=None):
        if chat_id:
            logger.info('overriding target chat id (%d) with %d', self._chat_id, chat_id)
            self._chat_id = chat_id

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
                elif self._s.media_type == MediaType.GFYCAT:
                    logger.info('post is a gfycat: using _send_gfycat()')
                    self._sent_message = self._send_gfycat(self._s.media_url, text)
                
                return self._sent_message
            except Exception as e:
                logger.error('exeption during the sending of a media, sending as text. Error: %s', str(e))
        else:
            logger.info('post is NOT a media, sending it as text')
        
        logger.info('posting a text...')
        self._sent_message = self._send_text(text)

        return self._sent_message

    def _upload_video(self, chat_id, file_path, pyrogram=False, *args, **kwargs):
        if not pyrogram:
            with open(file_path, 'rb') as f:
                logger.info('uploading video using the bot API...')
                return self._bot.send_video(chat_id, f, *args, **kwargs)
        else:
            logger.info('uploading video using mtproto...')
            with mtproto:
                return mtproto.upload_video(chat_id, file_path, *args, **kwargs)

    def _send_text(self, text):
        return self._bot.send_message(
            self._chat_id,
            text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=not self._subreddit.webpage_preview
        )

    def _send_image(self, image_url, caption):
        logger.info('image url: %s', image_url)
        
        self._sent_message = self._bot.send_photo(
            self._chat_id,
            image_url,
            caption=caption,
            parse_mode=ParseMode.HTML,
            timeout=360
        )
        
        return self._sent_message

    def _send_vreddit(self, url, caption):
        logger.info('vreddit url: %s', url)

        vreddit = VReddit(url, thumbnail_url=self._s.thumbnail, identifier=self._s.id, max_size=MaxSize.MTPROTO)
        logger.info('vreddit video url: %s', vreddit.url)
        logger.info('vreddit audio url: %s', vreddit.url_audio)

        if self._s.is_gif:
            logger.info('[1/2] vreddit is a GIF (does not have an audio): we will NOT try to download the audio and merge audio and video')
            logger.info('[2/2] the following logs will mention the merged audio/video, but we are now just handling the video')

        file_path = vreddit.file_path
        logger.info('file that will be used for the merged audio/video: %s', vreddit.merged_path)
        try:
            logger.info('downloading video/audio and merging them...')
            file_path = vreddit.download_and_merge(skip_audio=True if self._s.is_gif else False)
            logger.info('...merging ended. File size: %s', vreddit.size_readable)
            logger.info('file path of the video we will send: %s', file_path)
        except FileTooBig:
            logger.info('video is too big to be sent (%s), removing file and sending text...', vreddit.size_readable)
            vreddit.remove()
            raise FileTooBig
        except FfmpegTimeoutError:
            logger.info('ffmpeg timeout error during the merging of video/audio')
            vreddit.remove()
            raise FfmpegTimeoutError

        logger.info('downloading thumbnail from url: %s', vreddit.thumbnail_url)
        vreddit.download_thumbnail()
        logger.info('thumbnail path: %s', vreddit.thumbnail_path)

        if vreddit.size > MaxSize.BOT_API:
            self._sent_message = self._upload_video(
                self._chat_id,
                file_path,
                pyrogram=True,
                caption=caption,
                parse_mode=ParseMode.HTML,
                thumb=vreddit.thumbnail_path,
                height=self._s.video_size[0],
                width=self._s.video_size[1],
                duration=self._s.video_duration,
                supports_streaming=True
            )
        else:
            self._sent_message = self._upload_video(
                self._chat_id,
                file_path,
                pyrogram=False,
                caption=caption,
                parse_mode=ParseMode.HTML,
                thumb=vreddit.get_thumbnail_bo(),
                height=self._s.video_size[0],
                width=self._s.video_size[1],
                duration=self._s.video_duration,
                supports_streaming=True,
                timeout=360
            )

        logger.info('removing downloaded files...')
        vreddit.remove()

        return self._sent_message

    def _send_video(self, url, caption):
        logger.info('video url: %s', url)

        video = Downloader(url, identifier=self._s.id)
        logger.info('video path: %s', video.file_path)
        try:
            logger.info('downloading video...')
            video.download()
            logger.info('...download ended. File size: %s', video.size_readable)
        except FileTooBig:
            logger.info('video is too big to be sent (%s), removing file and sending text...', video.size_readable)
            video.remove(keep_thumbnail=True)
            
            raise FileTooBig
        
        video.thumbnail_path = 'assets/video_thumb.png'  # generic thumbnail
        
        logger.debug('opening and sending video...')
        with open(video.file_path, 'rb') as f:
            self._sent_message = self._bot.send_video(
                self._chat_id,
                f,
                caption=caption,
                thumb=video.get_thumbnail_bo(),
                height=None,
                width=None,
                duration=None,
                parse_mode=ParseMode.HTML,
                supports_streaming=True,
                timeout=360
            )
        logger.debug('...upload completed')

        logger.info('removing downloaded files...')
        video.remove(keep_thumbnail=True)
        # DO NOT DELETE THE GENERIC THUMBNAIL FILE
        
        return self._sent_message
    
    def _send_gif(self, url, caption):
        logger.info('gif url: %s', url)

        return self._bot.send_animation(
            self._chat_id,
            url,
            caption=caption,
            parse_mode=ParseMode.HTML,
            timeout=360
        )

    def _send_gfycat(self, url, caption):
        gfycat = Gfycat(url)
        logger.info('gfycat url: %s', gfycat.url)

        gfycat.download_thumbnail()

        sent_message = self._bot.send_video(
            self._chat_id,
            gfycat.url,
            caption=caption,
            parse_mode=ParseMode.HTML,
            width=gfycat.sizes[0],
            height=gfycat.sizes[1],
            thumb=gfycat.get_thumbnail_bo(),
            duration=gfycat.duration,
            timeout=360
        )

        gfycat.remove()

        return sent_message
    
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
        elif self._subreddit.min_score and isinstance(self._subreddit.min_score, int) and self._subreddit.min_score > self._s.score:
            logger.info('tests failed: not enough upvotes (%d/%d)', self._s.score, self._subreddit.min_score)
            return False
        elif self._subreddit.allow_nsfw is not None and self._subreddit.allow_nsfw == False and self._s.over_18:
            logger.info('tests failed: submission is NSFW')
            return False
        elif self._subreddit.hide_spoilers and self._s.spoiler == True:
            logger.info('tests failed: submission is a spoiler')
            return False
        elif self._subreddit.ignore_if_newer_than \
                and isinstance(self._subreddit.ignore_if_newer_than, int) \
                and self._s.elapsed_minutes < self._subreddit.ignore_if_newer_than:
            logger.info(
                'tests failed: too new (submitted: %s, elapsed: %s, ignore_if_newer_than: %d)',
                self._s.created_utc_formatted,
                u.pretty_minutes(self._s.elapsed_minutes),
                self._subreddit.ignore_if_newer_than
            )
            return False
        else:
            return True
    
    def write_temp_submission_dict(self):
        text = pprint.pformat(self.submission_dict)
        file_path = os.path.join('downloads', '{}.temp.txt'.format(self._s.id))
    
        with open(file_path, 'w+') as f:
            f.write(text)
            
        return file_path
        



