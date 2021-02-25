import logging
import re

from telegram import Update
from telegram.ext import CallbackContext

from bot.conversation import Status
from database.models import Subreddit
from utilities import u
from utilities import d

logger = logging.getLogger('handler')

REGEX_PATTERN = r'(?:(?P<hours>\d+) *h *)?(?: *(?P<minutes>\d+) *m)?'


class TimeParser:
    def __init__(self, string, safe_threshold=1):
        match = re.search(REGEX_PATTERN, string, re.I)
        if not match:
            raise ValueError('malformed pattern')

        match_dict = match.groupdict()

        self.hours = int(match_dict.get('hours', 0) or 0)
        self.minutes = int(match_dict.get('minutes', 0) or 0)

        if not self.hours and not self.minutes:
            raise ValueError('malformed pattern')

        self.total_minutes = self.minutes + (self.hours * 60)
        self.total_minutes_safe = self.total_minutes - safe_threshold


@d.restricted
@d.failwithmessage
@d.logconversation()
@d.pass_subreddit
def subconfig_on_freq_command(update: Update, context: CallbackContext, subreddit: Subreddit):
    logger.info('/freq command')

    if not context.args:
        update.message.reply_text('You need to pass me a frequency')
        return Status.WAITING_SUBREDDIT_CONFIG_ACTION

    input_string = re.search(r'.freq +(.+)$', update.message.text, re.I).group(1)

    try:
        parsed_time = TimeParser(input_string)
    except ValueError as e:
        update.message.reply_html('Error while parsing the time: {} (usage: "<i>5h</i>" or "<i>3h 40m</i>" or "<i>50m</i>")'.format(str(e)))
        return Status.WAITING_SUBREDDIT_CONFIG_ACTION

    if parsed_time.total_minutes_safe < 1:
        update.message.reply_text('The number of minutes must be greater than 1 (your input: {})'.format(parsed_time.total_minutes_safe))
        return Status.WAITING_SUBREDDIT_CONFIG_ACTION

    subreddit.max_frequency = parsed_time.total_minutes_safe
    subreddit.save()

    update.message.reply_html('<code>max_frequency</code> saved: {}'.format(parsed_time.total_minutes_safe))

    return Status.WAITING_SUBREDDIT_CONFIG_ACTION
