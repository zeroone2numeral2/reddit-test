import logging
import re

from playhouse.shortcuts import model_to_dict
from telegram.ext import CommandHandler
from ptbplugins import Plugins

from database.models import Subreddit
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['setting', 'set'], pass_args=True)
@d.restricted
@d.failwithmessage
@d.knownsubreddit
def sub_settings(_, update, args):
    logger.info('/set command (args: %s)', args)

    if len(args) < 3:
        update.message.reply_html('Use the following format: <code>/set [name] [setting] [new value]</code>')
        return

    # use the first two args values
    subreddit_name, setting = args[:2]
    setting = setting.lower()
    logger.info('subreddit_name, setting: %s, %s', subreddit_name, setting)

    # use the remaining text portion
    value = re.search(r'^\/\w+\s+[\w-]{3,22}\s+\w+\s+((?:.|\s)+)$', update.message.text, re.I).group(1)
    logger.info('value: %s', value)

    subreddit = Subreddit.fetch(subreddit_name)
    subreddit_dict = model_to_dict(subreddit)
    try:
        subreddit_dict[setting]
    except KeyError:
        update.message.reply_text('Cannot find field "{}" in the database row'.format(setting))
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
        setattr(subreddit, setting, value)
        subreddit.save()
    except Exception as e:
        logger.error('error while setting subreddit object property (%s, %s): %s', setting, str(value), str(e), exc_info=True)
        update.message.reply_text('Error while setting the property: {}'.format(str(e)))
        return

    new_value = getattr(subreddit, setting)

    update.message.reply_html('Done\n<code>{setting}</code>: {new_value}\n\nValue type: <code>{input_type}</code>'.format(
        setting=setting,
        new_value=u.escape(str(new_value)),
        input_type=u.escape(str(type(value).__name__))
    ))
