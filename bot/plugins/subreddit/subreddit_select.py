import logging
import re

from telegram.ext import MessageHandler, CommandHandler
from telegram.ext import Filters
from telegram.ext import ConversationHandler
from ptbplugins import Plugins
from database.models import Subreddit

from bot.markups import Keyboard
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)

SUBREDDIT_SELECT = 0

TEXT = """You are configuring /r/{s.name} (channel: {s.channel.title})

<b>Available commands</b>: \
/info, \
/remove (remove the subreddit from the db), \
/setchannel (set the subreddit's channel), \
/clonefrom (override the settings of the current subreddit with those from another one), \
/setchannelicon (use this subreddit's icon as channel icon), \
/disable (disable the subreddit)

You can also pass one of the subreddit's properties to see or change them, for example:
• "<code>template</code>" will show the current template
• "<code>max_frequency 295</code>" will change <code>max_frequency</code> to 295

Use /end when you are done\
"""


@d.restricted
@d.failwithmessage
def on_sub_command(_, update, args):
    logger.debug('/sub: selecting subreddit, text: %s', update.message.text)

    name_filter = args[0] if args else None

    subreddits = Subreddit.get_list(name_filter=name_filter)
    if not subreddits:
        update.message.reply_text('Cannot find any subreddit (filter: {})'.format(name_filter))
        return ConversationHandler.END

    reply_markup = Keyboard.from_list(['{}. /r/{} ({})'.format(s.id, s.name, s.channel.title) for s in subreddits])

    update.message.reply_text('Select the subreddit (or /cancel):', reply_markup=reply_markup)

    return SUBREDDIT_SELECT


@d.restricted
@d.failwithmessage
def on_subreddit_selected(_, update, user_data=None):
    logger.info('/sub command: subreddit selected (%s)', update.message.text)

    subreddit_key = int(re.search(r'(\d+)\. .*', update.message.text, re.I).group(1))
    logger.debug('subreddit id: %d', subreddit_key)

    subreddit = Subreddit.get(Subreddit.id == subreddit_key)

    user_data['data'] = dict()
    user_data['data']['subreddit'] = subreddit

    text = TEXT.format(s=subreddit)

    update.message.reply_html(text, disable_web_page_preview=True, reply_markup=Keyboard.REMOVE)

    return ConversationHandler.END


@d.restricted
@d.failwithmessage
def on_cancel(_, update, user_data):
    logger.debug('ending conversation')

    update.message.reply_text('Okay, operation canceled', reply_markup=Keyboard.REMOVE)

    user_data.pop('subreddit', None)

    return ConversationHandler.END


@Plugins.add(CommandHandler, command=['end'], pass_user_data=True)
@d.restricted
@d.failwithmessage
@d.pass_subreddit(answer=True)
def on_end(_, update, user_data=None, subreddit=None):
    logger.debug('/end command')

    text = 'Exited configuration mode for /r/{s.name} (channel: {s.channel.title})'.format(s=subreddit)

    user_data.pop('data', None)

    update.message.reply_text(text)


@Plugins.add_conversation_hanlder()
def info_subreddit_conv_hanlder():
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler(command=['sub', 'subreddit'], callback=on_sub_command, pass_args=True)],
        states={
            SUBREDDIT_SELECT: [MessageHandler(Filters.text, callback=on_subreddit_selected, pass_user_data=True)],
        },
        fallbacks=[CommandHandler(['cancel', 'done'], on_cancel, pass_user_data=True)]
    )

    return conv_handler
