import logging

from telegram import Update, ChatMember
from telegram.ext import ConversationHandler, CallbackContext
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters

from bot import mainbot
from bot.markups import Keyboard
from database.models import Channel
from utilities import u
from utilities import d

logger = logging.getLogger('handler')

CHANNEL_SELECT = range(1)

VALID_SUB_REGEX = r'(?:\/?r\/?)?([\w-]{3,22})'


@d.restricted
@d.failwithmessage
def on_getadmins_command(update: Update, context: CallbackContext):
    logger.info('/getadmins command')

    channels_list = Channel.get_list()
    if not channels_list:
        update.message.reply_text('No saved channel. Use /addchannel to add a channel')
        return ConversationHandler.END

    if len(context.args) > 0:
        channel_title_filter = context.args[0].lower()
        channels_list = [c for c in channels_list if channel_title_filter in c.lower()]

    reply_markup = Keyboard.from_list(channels_list)
    update.message.reply_text('Select the channel (or /cancel):', reply_markup=reply_markup)

    return CHANNEL_SELECT


@d.restricted
@d.failwithmessage
def on_channel_selected(update: Update, context: CallbackContext):
    logger.info('channel selected: %s', update.message.text)

    channel_id = u.expand_channel_id(update.message.text)
    logger.info('channel_id: %d', channel_id)

    admins: [ChatMember] = context.bot.get_chat_administrators(channel_id)
    users = list()
    bot_chat_member_dict: [ChatMember, None] = None
    for admin in admins:
        if admin.status == ChatMember.CREATOR:
            users.insert(0, 'owner: ' + admin.user.mention_html())
        else:
            users.append(admin.user.mention_html())

        if admin.user.id == mainbot.bot.id:
            bot_chat_member_dict = admin.to_dict()

    text = '\n'.join(users) + '\n\n<b>Bot permissions</b>:'

    for k, v in bot_chat_member_dict.items():
        if k.startswith('can_'):
            text += '\n<code>{}</code>: {}'.format(k, str(v).lower())

    update.message.reply_html(text, reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_cancel(update, _):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted', reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


mainbot.add_handler(ConversationHandler(
    entry_points=[CommandHandler(command=['getadmins'], callback=on_getadmins_command)],
    states={
        CHANNEL_SELECT: [
            MessageHandler(Filters.text & ~Filters.command, callback=on_channel_selected)
        ]
    },
    fallbacks=[
        CommandHandler('cancel', on_cancel)
    ]
))
