import logging
from collections import OrderedDict

from telegram.ext import CommandHandler

from bot import Plugins
from utilities import d
from utilities import u
from database.models import Subreddit
from reddit import Sender
from reddit import reddit

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['placeholders', 'ph'])
@d.restricted
@d.failwithmessage
def subs_list(bot, update):
    logger.info('/placeholders command')

    template_keys = list()
    template_kv = dict()

    sender = None
    subreddit = Subreddit.select().get()
    for submission in reddit.iter_submissions(subreddit.name, limit=1):
        sender = Sender(bot, subreddit, submission)

        template_keys = sender.template_keys
        break

    for key in template_keys:
        if key not in ('STR_FIELD',):
            val = getattr(sender.submission, key)
            template_kv[key] = str(type(val))

    template_kv = OrderedDict(sorted(template_kv.items()))
    
    placeholders = ['<code>{}</code> {}'.format(key.strip(), u.html_escape(val)) for key, val in template_kv.items()]
    update.message.reply_html('\n'.join(placeholders))
