import logging

from playhouse.shortcuts import model_to_dict
from telegram.ext import CommandHandler

from database.models import Subreddit
from bot import Plugins
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['get'], pass_args=True)
@d.restricted
@d.failwithmessage
@d.knownsubreddit
def sub_get_setting(_, update, args):
    logger.info('/get command (args: %s)', args)

    if len(args) < 2:
        update.message.reply_html('Use the following format: <code>/get [name] [setting]</code>')
        return

    # use the first two args values
    subreddit_name, setting = args[:2]
    setting = setting.lower()
    logger.info('subreddit_name, setting: %s, %s', subreddit_name, setting)

    subreddit = Subreddit.fetch(subreddit_name)
    subreddit_dict = model_to_dict(subreddit)
    try:
        subreddit_dict[setting]
    except KeyError:
        update.message.reply_text('Cannot find field "{}" in the database row'.format(setting))
        return

    value = getattr(subreddit, setting)
    
    update.message.reply_text('{}:'.format(setting))
    update.message.reply_html('<code>{}</code>'.format(u.escape(str(value))))
