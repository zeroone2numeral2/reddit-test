import logging

from telegram import Update
from telegram.ext import CallbackContext

from bot.conversation import Status
from database.models import Subreddit
from database.models import Channel
from bot.markups import Keyboard
from utilities import u
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation()
def subconfig_on_setchannel_command(update: Update, context: CallbackContext):
    logger.info('setchannel callback: %s', update.message.text)

    channels_list = Channel.get_list()
    if not channels_list:
        update.message.reply_text('No saved channel. Use /end and /addchannel to add a channel')
        return Status.WAITING_SUBREDDIT_CONFIG_ACTION

    if len(context.args) > 0:
        channel_title_filter = context.args[0].lower()
        channels_list = [c for c in channels_list if channel_title_filter in c.lower()]

    reply_markup = Keyboard.from_list(channels_list)
    update.message.reply_text(
        'Select the new channel, or /cancel:',
        reply_markup=reply_markup
    )

    return Status.SETCHANNEL_WAITING_CHANNEL


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_subreddit
def subconfig_on_selected_channel(update: Update, _, subreddit: Subreddit):
    logger.info('channel selected: %s', update.message.text)

    channel_id = u.expand_channel_id(update.message.text)
    channel = Channel.get(Channel.channel_id == channel_id)

    subreddit.channel = channel
    subreddit.save()

    update.message.reply_text('r/{}\'s channel saved: {}'.format(subreddit.name, channel.title), reply_markup=Keyboard.REMOVE)

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION


@d.restricted
@d.failwithmessage
@d.logconversation()
def subconfig_on_selected_channel_wrong(update: Update, _):
    logger.info('unexpected message while selecting channel')
    update.message.reply_text('Select a channel, or /cancel')

    return Status.SETCHANNEL_WAITING_CHANNEL
