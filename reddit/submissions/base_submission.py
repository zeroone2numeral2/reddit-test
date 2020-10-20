import logging

from telegram import Bot

from const import MaxSize
from utilities import u
from pyroutils import PyroClient
from config import config

logger = logging.getLogger('sp')


mtproto = PyroClient(
    config.pyrogram.session_name,
    bot_token=config.telegram.token,
    api_id=config.pyrogram.api_id,
    api_hash=config.pyrogram.api_hash,
    workers=config.pyrogram.workers,
    no_updates=True
)


class BaseSenderType:
    # The EXTERNAL_CONTENT flag signals whether this class is used for url that link to some content which is
    # supposed to be consumed outiside of Reddit. For example, Twitter links and YouTube links are external content,
    # but vreddit urls/direct urls to images/imgur urls (imgur is a social, but on reddit it is mainly used as an images hosting service)
    # are ment to link some content that doesn't live on external platforms. This will be used to decide which
    # template to use
    EXTERNAL_CONTENT = False

    def __init__(self, submission, subreddit, bot):
        self._submission = submission
        self._subreddit = subreddit
        self.chat_id = self._subreddit.channel.channel_id
        self._bot: Bot = bot
        self._uploaded_bytes = 0
        self.sent_messages: list = []

        if hasattr(subreddit, 'logger'):
            self.log = subreddit.logger
        else:
            self.log = logger

    @property
    def uploaded_bytes(self):
        return self._uploaded_bytes

    def sent_messages_to_list(self):
        if isinstance(self.sent_messages, list):
            return False

        self.sent_messages = [self.sent_messages]
        return True

    def _entry_point(self, *args, **kwargs):
        raise NotImplementedError('this method must be overridden')

    def post(self, *args, **kwargs):
        self.sent_messages = self._entry_point(*args, **kwargs)
        self.sent_messages_to_list()

        return self.sent_messages

    def _sum_uploaded_bytes(self, sent_message):
        uploaded_bytes = u.media_size(sent_message) or 0
        # logger.debug('registering we sent %d bytes (%s)', uploaded_bytes, u.human_readable_size(uploaded_bytes))

        self._uploaded_bytes += uploaded_bytes

    def _upload_video(self, chat_id, file_path, file_size=0, force_bot_api=False, *args, **kwargs):
        if file_size < MaxSize.BOT_API or force_bot_api or not config.pyrogram.enabled:
            self.log.debug('sending using the bot API because: file size is small OR method caller asked to use the bot api OR mtproto uploads disabled from config')
            kwargs['thumb'] = kwargs['thumb_bo']
            kwargs.pop('thumb_path', None)  # remove kwargs send_video doesn't accept
            with open(file_path, 'rb') as f:
                self.log.info('uploading video using the bot API...')
                return self._bot.send_video(chat_id, f, *args, **kwargs)
        else:
            # client.send_video doesn't accept unknown arguments
            kwargs['thumb'] = kwargs.pop('thumb_path', None)
            kwargs.pop('thumb_bo', None)
            kwargs.pop('timeout', None)

            self.log.info('uploading video using mtproto (file size: %d (%s), max bot API: %d)...', file_size,
                          u.human_readable_size(file_size), MaxSize.BOT_API)
            with mtproto:
                self.log.debug('mtproto upload started at %s', u.now(string='%d/%m/%Y %H:%M:%S'))
                sent_message = mtproto.upload_video(chat_id, file_path, *args, **kwargs)
                self.log.debug('mtproto upload ended at %s', u.now(string='%d/%m/%Y %H:%M:%S'))

                # self.log.debug('client.send_video() result: %s', str(sent_message))

                return sent_message
