import logging

from telegram.ext import CommandHandler
from ptbplugins import Plugins

from database.models import Subreddit
from utilities import u
from utilities import d

logger = logging.getLogger(__name__)


@Plugins.add(CommandHandler, command=['clone'], pass_args=True)
@d.restricted
@d.failwithmessage
@d.knownsubreddit
def sub_clone(_, update, args):
    logger.info('/clone command (args: %s)', args)

    origin_name = args[0]
    if len(args) < 2:
        update.message.reply_text("Pass the subreddit of which we're cloning {}'s settings to".format(origin_name))
        return

    dest_name = args[1]

    origin_sub = Subreddit.fetch(origin_name)
    dest_sub = Subreddit.fetch(dest_name)

    if not dest_sub:
        update.message.reply_text('No "{}" in the database'.format(dest_name))
        return

    origin_dict = u.model_dict(origin_sub, plain_formatted_string=False)
    for key in ('subreddit_id', 'name', 'channel', 'last_posted_submission_dt', 'added'):
        # we don't have to override these fields
        origin_dict.pop(key, None)

    Subreddit.update(**origin_dict).where(Subreddit.subreddit_id == dest_sub.subreddit_id).execute()

    update.message.reply_text('"{}" settings cloned to "{}"'.format(origin_name, dest_name))
