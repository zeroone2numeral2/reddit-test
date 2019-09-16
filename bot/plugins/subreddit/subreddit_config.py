import logging
import re

from playhouse.shortcuts import model_to_dict
from telegram.ext import ConversationHandler
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import Filters
from ptbplugins import Plugins

from bot.markups import Keyboard
from database.models import Subreddit
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)

SUBREDDIT_SELECT, CHANGE_CONFIG = range(2)


@d.restricted
@d.failwithmessage
def on_config_command(_, update, args):
    logger.info('/config command, args: %s', str(args))

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
def on_subreddit_selected(_, update, user_data):
    logger.info('subreddit selected: %s', update.message.text)

    subreddit_key = int(re.search(r'(\d+)\. .*', update.message.text, re.I).group(1))
    logger.info('subreddit key: %d', subreddit_key)

    subreddit = Subreddit.get(Subreddit.id == subreddit_key)

    user_data['subreddit'] = subreddit

    update.message.reply_text(
        'Selected subreddit: /r/{s.name} (channel: {s.channel.title}). You can now change its configuration'.format(s=subreddit),
        reply_markup=Keyboard.REMOVE
    )

    return CHANGE_CONFIG


@d.restricted
@d.failwithmessage
def on_setting_change(_, update, user_data):
    logger.info('changed subreddit property: %s', update.message.text)

    logger.info('subreddit_name: %s', user_data['subreddit'].name)

    # extract values
    match = re.search(r'^(\w+)\s+(.+)', update.message.text, re.I)
    if not match:
        update.message.reply_text('Use the following format: [key] [new value]')
        return CHANGE_CONFIG

    key = match.group(1)
    value = match.group(2)
    logger.info('key: %s; value: %s', key, value)

    subreddit_dict = model_to_dict(user_data['subreddit'])
    try:
        subreddit_dict[key]
    except KeyError:
        update.message.reply_text('Cannot find field "{}" in the database row'.format(key))
        return CHANGE_CONFIG

    if value in ('true', 'True'):
        logger.info('value is True')
        value = True
    elif value in ('false', 'False'):
        logger.info('value is False')
        value = False
    elif value in ('none', 'None'):
        logger.info('value is None')
        value = None
    elif re.search(r'^\d+$', value, re.I):
        logger.info('value is int')
        value = int(value)
    elif re.search(r'^\d+\.\d+$', value, re.I):
        logger.info('value is float')
        value = float(value)
    logger.info('value after true/false/none/int/float check: %s', value)

    try:
        setattr(user_data['subreddit'], key, value)
        user_data['subreddit'].save()
    except Exception as e:
        logger.error('error while setting subreddit object property (%s, %s): %s', key, str(value), str(e), exc_info=True)
        update.message.reply_text('Error while setting the property: {}'.format(str(e)))
        return CHANGE_CONFIG

    new_value = getattr(user_data['subreddit'], key)

    update.message.reply_html('Done\n<code>{setting}</code>: {new_value}\n\nValue type: <code>{input_type}</code>\n\nUse /done when you are done'.format(
        setting=key,
        new_value=u.escape(str(new_value)),
        input_type=u.escape(str(type(value).__name__))
    ))

    return CHANGE_CONFIG


@d.restricted
@d.failwithmessage
def on_cancel(_, update, user_data):
    logger.info('conversation canceled with /cancel')
    update.message.reply_text('Operation aborted/completed', reply_markup=Keyboard.REMOVE)

    user_data.pop('subreddit', None)

    return ConversationHandler.END


@Plugins.add_conversation_hanlder()
def config_subreddit_conv_hanlder():
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler(command=['config'], callback=on_config_command, pass_args=True)],
        states={
            SUBREDDIT_SELECT: [
                MessageHandler(Filters.text, callback=on_subreddit_selected, pass_user_data=True)
            ],
            CHANGE_CONFIG: [
                MessageHandler(Filters.text, callback=on_setting_change, pass_user_data=True)
            ]
        },
        fallbacks=[
            CommandHandler(['cancel', 'done'], on_cancel, pass_user_data=True)
        ]
    )

    return conv_handler