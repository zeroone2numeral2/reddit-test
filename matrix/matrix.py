import os
import logging

from matrix_client.client import MatrixClient
from matrix_client.api import MatrixHttpApi

from utilities import u
from config import config

logger = logging.getLogger(__name__)

# photo_path = r'C:\Users\riccardo\Desktop\h7nt4keyd7oy.jpg'
# room_id = "!MZJhJgkhKDpxLvTxXe:matrix.org"


class MsgType:
    # https://matrix.org/docs/spec/r0.0.1/client_server.html#m-room-message-msgtypes
    TEXT = 'm.text'
    EMOTE = 'm.emote'
    NOTICE = 'm.notice'
    IMAGE = 'm.image'
    FILE = 'm.file'
    LOCATION = 'm.location'
    VIDEO = 'm.video'
    AUDIO = 'm.audio'


class Matrix:
    def __init__(self):
        self._client = MatrixClient(config.matrix.server)
        self._token = self._client.login(username=config.matrix.username, password=config.matrix.password, sync=False)
        self._api = MatrixHttpApi(config.matrix.server, self._token)
    
    def _upload(self, file_path):
        mimetype = u.guess_mimetype(file_path)
        
        with open(file_path, 'rb') as f:
            result = self._api.media_upload(f, mimetype)
        
        return result['content_uri']
    
    def send_text(self, room_id, text):
        self._api.send_message(room_id, text)
    
    def send_emote_html(self, room_id, text):
        content = dict(
            body=text,
            format='org.matrix.custom.html',
            formatted_body=text,
            msgtype=MsgType.EMOTE
        )
        
        self._api.send_message_event(room_id, event_type="m.room.message", content=content)
    
    def send_notice(self, room_id, text):
        self._api.send_notice(room_id, text)
    
    def send_photo(self, room_id, file_path):
        file_path = os.path.normpath(file_path)
        file_name = os.path.basename(file_path)
        
        url = self._upload(file_path)
        
        self._api.send_content(room_id, url, file_name, MsgType.IMAGE)
    
    def send_video(self, room_id, file_path):
        file_path = os.path.normpath(file_path)
        file_name = os.path.basename(file_path)
        
        url = self._upload(file_path)
        
        self._api.send_content(room_id, url, file_name, MsgType.VIDEO)