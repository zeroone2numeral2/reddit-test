import logging
from pprint import pprint

from telegram.ext import CommandHandler
from telegram import InputMediaPhoto, InputMediaVideo

from bot import mainbot
from utilities import d
from reddit import reddit
from reddit.downloaders import Imgur
from reddit.submissions.imgur import imgur
from config import config

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def on_imgur_command(update, context):
    logger.info('/imgur command')

    arg = context.args[0].strip()
    imgur = Imgur(config.imgur.id, config.imgur.secret)

    urls = imgur.parse_album(arg)
    print(urls)

    media_group = list()
    for i, url in enumerate(urls):
        if url.endswith(('.jpg', '.png')):
            input_media = InputMediaPhoto(media=url)
        elif url.endswith('.mp4'):
            input_media = InputMediaVideo(media=url)
        elif url.endswith('.gifv'):
            url = url.replace('.gifv', '.mp4')
            input_media = InputMediaVideo(media=url)
        elif url.endswith('.gif'):
            url = url.replace('.gif', '.mp4')
            input_media = InputMediaVideo(media=url)
        else:
            continue

        media_group.append(input_media)

    if not media_group:
        raise ValueError('media_group is empty')

    update.message.reply_media_group(media=media_group)


mainbot.add_handler(CommandHandler('imgur', on_imgur_command))
