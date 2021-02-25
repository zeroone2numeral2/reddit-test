import logging

from telegram import Update
from telegram.ext import ConversationHandler, CallbackContext

from bot.conversation import Status
from bot.markups import Keyboard, InlineKeyboard
from database.models import Channel
from database.models import Subreddit
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_channel
def channelconfig_on_confirm_delete_callbackquery(update: Update, context: CallbackContext, channel: Channel):
    logger.debug("deletion confirmed, %s", context.matches)

    channel_subreddits = Subreddit.linked_to_channel(channel)
    for subreddit in channel_subreddits:
        subreddit.channel = None
        subreddit.save()
        logger.debug('removed bind channel for subreddit %s', subreddit.r_name)

    channel_title = channel.title

    logger.info('Deleting channel...')
    channel.delete_instance()

    update.effective_message.edit_text(
        'Channel "{}" removed. Orphan subreddits: {}'.format(
            channel_title,
            ', '.join([s.name for s in channel_subreddits]) if channel_subreddits else 'none'
        ),
        reply_markup=InlineKeyboard.REMOVE
    )

    context.user_data.pop("data", None)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_channel
def channelconfig_on_remove_command(update: Update, context: CallbackContext, channel: Channel):
    logger.info('/remove')

    channel_subreddits = Subreddit.linked_to_channel(channel)
    if channel_subreddits:
        subreddit_names = []
        for subreddit in channel_subreddits:
            subreddit_names.append(subreddit.r_name)

        text = "There are currently {} subreddit using this channel:".format(len(channel_subreddits))
        for subreddit in channel_subreddits:
            text += "\n{} ({})".format(subreddit.r_name, "enabled" if subreddit.enabled else "disabled")

        update.message.reply_text(text, reply_markup=Keyboard.REMOVE)

        update.message.reply_html(
            "Are you sure you want to forget this channel? Its subreddits will be orphan (but will not be deleted)",
            reply_markup=InlineKeyboard.forget_channel(channel.channel_id)
        )

        return Status.WAITING_CHANNEL_CONFIG_ACTION

    channel_title = channel.title

    logger.info('deleting channel...')
    channel.delete_instance()

    update.message.reply_text(
        'Channel "{}" removed (no subreddit was using this channel)'.format(channel_title),
        reply_markup=Keyboard.REMOVE
    )

    context.user_data.pop("data", None)

    return ConversationHandler.END  # exit the conversation if we remove the channel
