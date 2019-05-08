import logging
import shutil

import requests
from telegram import Bot
from telegram import InputMediaPhoto
from telegram import InputMediaVideo
from telegram import InputMediaAnimation
from telegram import MAX_FILESIZE_DOWNLOAD

from reddit import reddit
from reddit import Sender
from reddit.downloaders import Imgur
from database.models import Subreddit
from utilities import l
from config import config

logger = logging.getLogger(__name__)
bot = Bot(config.telegram.token)

SUB_NAME = 'ricardo_test'

l.load_logging_config(config.logging.config, config.logging.filepath)


IGNORE_SUBMISSIONS = [
    'b3zaqd',  # vreddit with sound
    'b3z78n',  # direct mp4 url
    'b581fm'  # large vreddit
]


def test():
    imgur = Imgur(keys_from_config=True)

    album_urls = [
        # 'https://imgur.com/gallery/O866Q',
        'https://imgur.com/a/l9A1Z',
        # 'https://imgur.com/a/EPVZsAh',  # custom
    ]
    for album_url in album_urls:
        urls = imgur.parse_album(album_url, limit=10)
        print(urls)

        input_medias = list()
        for url in urls:
            media = Sender._parse_media(url, 'imgur.com', 'imgur.com', {})
            print('url:', media.url)

            r_result = requests.head(media.url)
            print(r_result.headers)

            if media.url.endswith(('.jpg', '.png')):
                input_medias.append(InputMediaPhoto(url))
                # bot.send_photo(23646077, media.url)
            elif media.type == 'video':
                input_medias.append(InputMediaVideo(url))
                bot.send_video(23646077, media.url)
            elif media.type == 'gif':
                input_medias.append(InputMediaAnimation(url))
                bot.send_animation(23646077, media.url)




        print(input_medias)
        # bot.send_media_group(23646077, input_medias)


def main():

    test()
    return

    logger.info('starting...')
    rtest = Subreddit.fetch(SUB_NAME)
    if not rtest:
        print(SUB_NAME, 'not in db')
        return
    
    for submission in reddit.iter_submissions(SUB_NAME, 'hot', limit=10):
        if submission.id in IGNORE_SUBMISSIONS:
            continue
        
        logger.info('')
        logger.info('')
        logger.info('')
        logger.info('TITLE: %s (%s) (%s)', submission.title, submission.id, submission.url)
        
        sender = Sender(bot, rtest, submission)
        
        if sender.test_filters():
            logger.info('submission passed filters')
        else:
            logger.info('submission does not pass filters')
        
        sender.post()


if __name__ == '__main__':
    main()
