import re
import random
from pprint import pprint

import requests

from reddit.downloaders import Downloader

GFYCAT_API = 'https://api.gfycat.com/v1/gfycats/'


class Gfycat(Downloader):
    def __init__(self, url, *args, **kwargs):
        Downloader.__init__(self, url, *args, **kwargs)

        video_id = re.search(r'gfycat.com/(?:detail/)?(\w*)', url).group(1)
        r = requests.get(GFYCAT_API + video_id)
        if r.status_code != 200:
            self._url = '{}.mp4'.format(url)
        else:
            r_json = r.json()
            self._url = r_json['gfyItem']['mp4Url']
            self._width = r_json['gfyItem']['width']
            self._height = r_json['gfyItem']['height']
            self._thumbnail_url = r_json['gfyItem']['thumb100PosterUrl']

    @property
    def sizes(self):
        return self._width, self._height
