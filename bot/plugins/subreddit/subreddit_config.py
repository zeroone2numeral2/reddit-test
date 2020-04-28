import logging
import re

from playhouse.shortcuts import model_to_dict
from telegram import Update
from telegram.ext import MessageHandler
from telegram.ext import Filters

from utilities import u
from utilities import d
from bot import CustomFilters, mainbot

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
# @d.deferred_handle_lock
@d.pass_subreddit(answer=True)
@d.logconversation
def on_setting_change(update: Update, _, subreddit):
    logger.info('changed subreddit property: %s', update.message.text)

    logger.info('subreddit_name: %s', subreddit.name)

    # just return the value if only one word is passed
    if re.search(r'^\w+$', update.message.text, re.I & re.M):
        setting = update.message.text.lower()
        subreddit_dict = model_to_dict(subreddit)

        try:
            subreddit_dict[setting]
        except KeyError:
            update.message.reply_text('Cannot find field "{}" in the database row'.format(setting))
            return

        value = getattr(subreddit, setting)

        update.message.reply_html('Current value of <code>{}</code>:'.format(setting))
        update.message.reply_html('<code>{}</code>'.format(u.escape(str(value))))

        return

    # extract values
    match = re.search(r'^(\w+)\s+((?:.|\s)+)$', update.message.text, re.I & re.M)
    if not match:
        update.message.reply_html('Use the following format: <code>[db field] [new value]</code>')
        return

    key = match.group(1)
    value = match.group(2)
    logger.info('key: %s; value: %s', key, value)

    subreddit_dict = model_to_dict(subreddit)
    try:
        subreddit_dict[key]
    except KeyError:
        update.message.reply_html('Cannot find field <code>{}</code> in the database row'.format(key))
        return

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
        setattr(subreddit, key, value)
        subreddit.save()
    except Exception as e:
        logger.error('error while setting subreddit object property (%s, %s): %s', key, str(value), str(e), exc_info=True)
        update.message.reply_text('Error while setting the property: {}'.format(str(e)))
        return

    new_value = getattr(subreddit, key)

    update.message.reply_html('Done, new value of <code>{setting}</code>: {new_value}\n\nValue type: <code>{input_type}</code>'.format(
        setting=key,
        new_value=u.escape(str(new_value)),
        input_type=u.escape(str(type(value).__name__))
    ))


mainbot.add_handler(MessageHandler(Filters.text & CustomFilters.subreddit_set & ~Filters.command, on_setting_change))
