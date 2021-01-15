import logging
import os

from telegram import Update
from telegram.ext import CallbackContext

from bot.conversation import Status
from database.models import Subreddit
from bot.markups import Keyboard
from reddit import Reddit, creds
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_subreddit
def subconfig_on_setchannelicon_command(update: Update, context: CallbackContext, subreddit: Subreddit):
    logger.info('/setchannelicon command')

    account = creds.default_account
    reddit = Reddit(**account.creds_dict(), **account.default_client.creds_dict())

    file_path = reddit.get_icon(subreddit.name, download=True)
    if not file_path:
        update.message.reply_text('Subreddit doesn\'t have an icon'.format(subreddit.name), reply_markup=Keyboard.REMOVE)
        return Status.WAITING_SUBREDDIT_CONFIG_ACTION

    with open(file_path, 'rb') as f:
        context.bot.set_chat_photo(subreddit.channel.channel_id, f)

    os.remove(file_path)

    update.message.reply_text('Icon updated')

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION
