import logging

from telegram import Update
from telegram.ext import CallbackContext

from bot.conversation import Status
from database.models import Channel
from database.models import Subreddit
from utilities import d

logger = logging.getLogger('handler')


@d.restricted
@d.failwithmessage
@d.logconversation
@d.pass_channel
def channelconfig_on_sproperty_command(update: Update, context: CallbackContext, channel: Channel):
    logger.info('/sproperty command, args: %s', context.args)

    channel_subreddits = Subreddit.linked_to_channel(channel)
    if not channel_subreddits:
        update.message.reply_text("No subreddit linked to this channel")
        return Status.WAITING_CHANNEL_CONFIG_ACTION

    setting = context.args[0].lower()

    values = {}
    for subreddit in channel_subreddits:
        subreddit_dict = subreddit.to_dict()

        try:
            subreddit_dict[setting]
        except KeyError:
            update.message.reply_text('Cannot find field "{}" for Subreddit model'.format(setting))
            return Status.WAITING_CHANNEL_CONFIG_ACTION

        value = getattr(subreddit, setting)

        values[subreddit.r_name] = value

    text = "Values for <code>{}</code>:\n\n{}".format(
        setting,
        "\n".join(["{}: <code>{}</code>".format(sub_name, value) for sub_name, value in values.items()])
    )
    update.message.reply_html(text)

    return Status.WAITING_CHANNEL_CONFIG_ACTION
