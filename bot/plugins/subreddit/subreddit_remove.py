import logging

from telegram import Update
from telegram.ext import CommandHandler, CallbackContext

from bot import mainbot
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.pass_subreddit(answer=True)
def delete_sub(update: Update, context: CallbackContext, subreddit=None):
    logger.info('/remove command')

    subreddit.delete_instance()

    channel_title = 'none'
    if subreddit.channel:
        channel_title = subreddit.channel.title

    update.message.reply_html(
        '/r/{s.name} (channel: {title}) has gone, you have also exited the configuring mode for this sub'.format(
            s=subreddit,
            title=channel_title
        )
    )

    context.user_data.pop('data', None)


mainbot.add_handler(CommandHandler(['rem', 'remove'], delete_sub, pass_user_data=True))
