import logging
from pprint import pprint

from telegram.ext import CommandHandler
from telegram import InputMediaPhoto

from bot import mainbot
from utilities import d
from reddit import reddit

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
def on_gallery_command(update, context):
    logger.info('/gallery command')

    submission_id = context.args[0].strip()
    submission = reddit.submission(id=submission_id)

    urls = list()
    for media_id, media_metadata in submission.media_metadata.items():
        # pprint(media_metadata)
        # print(submission.media_metadata[media_id]['p'][-1]['u'])
        print('type: {e}, id: {id}, mime: {m}'.format(**media_metadata))

        for size in media_metadata['p']:
            print('{x}x{y}: {u}'.format(**size))

        pprint('=' * 100)

        image_url = media_metadata['p'][-1]['u']
        urls.append(image_url)

    media_group = list()
    for i, url in enumerate(urls):
        media_group.append(InputMediaPhoto(media=url))

    update.message.reply_media_group(media=media_group)


mainbot.add_handler(CommandHandler('gallery', on_gallery_command))
