import logging

from telegram import Update, ChatMember
from telegram.ext import ConversationHandler, CallbackContext
from telegram.ext import MessageHandler
from telegram.ext import CommandHandler
from telegram.ext import Filters

from bot import mainbot
from bot.conversation import Status
from bot.markups import Keyboard
from .select_channel import channel_selection_handler
from utilities import u
from utilities import d

logger = logging.getLogger('handler')

VALID_SUB_REGEX = r'(?:\/?r\/?)?([\w-]{3,22})'


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
    entry_points=[CommandHandler(command=['getadmins'], callback=channel_selection_handler)],
    states={
        Status.CHANNEL_SELECTED: [
            MessageHandler(Filters.text & ~Filters.command, callback=on_channel_selected)
        ]
    },
    fallbacks=[
        CommandHandler('cancel', on_cancel)
    ]
))
