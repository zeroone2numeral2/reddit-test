import logging

from telegram import Update
from telegram.ext import ConversationHandler, CallbackContext, CallbackQueryHandler
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters

from bot import mainbot
from bot.conversation import Status
from bot.customfilters import CustomFilters
from bot.plugins.commands import Command
from bot.markups import Keyboard, InlineKeyboard
from database.models import Channel
from database.models import Subreddit
from .select_channel import channel_selection_handler, on_waiting_channel_selection_unknown_message
from utilities import u
from utilities import d

logger = logging.getLogger('handler')

VALID_SUB_REGEX = r'(?:\/?r\/?)?([\w-]{3,22})'


@d.restricted
@d.failwithmessage
def on_channel_selected(update, _):
    logger.info('channel selected: %s', update.message.text)

    channel_id = u.expand_channel_id(update.message.text)
    logger.info('channel_id: %d', channel_id)
    channel = Channel.get(Channel.channel_id == channel_id)

    channel_subreddits = Subreddit.linked_to_channel(channel)
    if channel_subreddits:
        for subreddit in channel_subreddits:
            subreddit.channel = None
            subreddit.save()
            logger.debug('removed bind channel for subreddit r/%s', subreddit.name)

    channel_title = channel.title
    
    logger.info('Deleting channel...')
    channel.delete_instance()
    
    update.message.reply_text(
        'Channel "{}" removed. Linked subreddits: {} (if any, their channel as been set to NULL)'.format(
            channel_title,
            ', '.join([s.name for s in channel_subreddits]) if channel_subreddits else 'none'
        ),
        reply_markup=Keyboard.REMOVE
    )

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_confirm_delete(update, context: CallbackContext):
    logger.debug("deletion confirmed, %s", context.matches)

    channel_id = context.matches[0].group(1)
    logger.info('channel_id: %d', channel_id)
    channel = Channel.get(Channel.channel_id == channel_id)

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

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_channel_selected_new(update, _):
    logger.info('channel selected: %s', update.message.text)

    channel_id = u.expand_channel_id(update.message.text)
    logger.info('channel_id: %d', channel_id)
    channel = Channel.get(Channel.channel_id == channel_id)

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
            reply_markup=InlineKeyboard.forget_channel(channel_id)
        )

        return Status.WAITING_CHANNEL_SELECTION

    channel_title = channel.title

    logger.info('deleting channel...')
    channel.delete_instance()

    update.message.reply_text(
        'Channel "{}" removed (no subreddit was using this channel)'.format(channel_title),
        reply_markup=Keyboard.REMOVE
    )

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_cancel(update, _):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


mainbot.add_handler(ConversationHandler(
    entry_points=[CommandHandler(command=['remchannel'], callback=channel_selection_handler)],
    states={
        Status.WAITING_CHANNEL_SELECTION: [
            MessageHandler(Filters.text & ~Filters.command, callback=on_channel_selected_new),
            CallbackQueryHandler(on_confirm_delete, pattern=r"delchannel:(.*)"),
            MessageHandler(CustomFilters.all_but_regex(Command.CANCEL_RE), on_waiting_channel_selection_unknown_message),
        ]
    },
    fallbacks=[
        CommandHandler(Command.CANCEL, on_cancel)
    ]
))
