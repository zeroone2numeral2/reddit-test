import logging

from pyrogram import Client

from ..reddit.downloaders import FileTooBig

logger = logging.getLogger(__name__)


class PyroClient(Client):
    def upload_video(self, chat_id, file_path, *args, **kwargs):
        try:
            self.send_video(chat_id, file_path, *args, **kwargs)
        except ValueError:
            logger.warning('file size is too big for pyrogram')
            raise FileTooBig
