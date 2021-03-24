import logging

from telegram import Update, ChatMember
from telegram.ext import CallbackContext

from bot import mainbot
from bot.markups import Keyboard
from bot.conversation import Status
from database.models import Channel
from utilities import d

logger = logging.getLogger('handler')

VALID_SUB_REGEX = r'(?:\/?r\/?)?([\w-]{3,22})'


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_channel
def channelconfig_on_getadmins_command(update: Update, context: CallbackContext, channel: Channel):
    logger.info("/getadmins")

    admins: [ChatMember] = context.bot.get_chat_administrators(channel.channel_id)
    users = list()
    bot_chat_member_dict: [ChatMember, None] = None
    for admin in admins:
        if admin.status == ChatMember.CREATOR:
            users.insert(0, 'owner: ' + admin.user.mention_html())
        else:
            users.append('admin: ' + admin.user.mention_html())

        if admin.user.id == mainbot.bot.id:
            bot_chat_member_dict = admin.to_dict()

    text = '\n'.join(users) + '\n\n<b>Bot permissions</b>:'

    for k, v in bot_chat_member_dict.items():
        if k.startswith('can_'):
            text += '\n<code>{}</code>: {}'.format(k, str(v).lower())

    update.message.reply_html(text, reply_markup=Keyboard.REMOVE)

    return Status.WAITING_CHANNEL_CONFIG_ACTION
