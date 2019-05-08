import re

from imgurpython import ImgurClient

from config import config

ALBUM_REGEX = re.compile(r'imgur\.com/(?:gallery|a)/(\w+)', re.I)


class InvalidAlbumUrl(Exception):
    pass


class Imgur(ImgurClient):
    def __init__(self, keys_from_config=False, *args, **kwargs):
        if not keys_from_config:
            ImgurClient.__init__(self, *args, **kwargs)
        else:
            ImgurClient.__init__(self, config.imgur.id, config.imgur.secret, *args, **kwargs)
    
    def get_url(self, image_id):
        return self.get_image(image_id).link
    
    def get_album_urls(self, album_id):
        return [image.link for image in self.get_album_images(album_id)]

    def parse_album(self, album_url):
        match = ALBUM_REGEX.search(album_url)
        if not match:
            raise InvalidAlbumUrl

        album_id = match.group(1)
        return self.get_album_urls(album_id)

    @staticmethod
    def is_album(url):
        match = ALBUM_REGEX.search(url)
        return bool(match)
