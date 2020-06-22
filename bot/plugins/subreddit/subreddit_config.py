import logging
import re

from playhouse.shortcuts import model_to_dict
from telegram import Update
from telegram.ext import MessageHandler
from telegram.ext import Filters

from utilities import u
from utilities import d
from bot import mainbot
from bot.customfilters import CustomFilters
from reddit import accounts
from reddit.sortings import ALL_SORTINGS

logger = logging.getLogger('handler')


def standard_conversion(value):
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

    return value


class TypesMap:
    BOOL_OR_NONE = dict(
        true=True,
        false=False,
        none=None
    )
    BOOL_ONLY = dict(
        true=True,
        false=False
    )


class Validator:
    BOOL = dict(
        convert=lambda value: TypesMap.BOOL_ONLY[value.lower()],
        test=lambda value: value.lower() in TypesMap.BOOL_ONLY,
        fail_error="not in {}".format(', '.join(TypesMap.BOOL_ONLY))
    )
    BOOL_OR_NONE = dict(
        convert=lambda value: TypesMap.BOOL_OR_NONE[value.lower()],
        test=lambda value: value.lower() in TypesMap.BOOL_OR_NONE,
        fail_error="not in {}".format(', '.join(TypesMap.BOOL_OR_NONE))
    )
    INT = dict(
        test=lambda value: bool(re.search(r'^\d+$', value)),
        fail_error="not an int",
        convert=lambda value: int(value)
    )
    FLOAT = dict(
        convert=lambda value: float(value),
        test=lambda value: bool(re.search(r'^\d+(?:[.,]\d+)?$', value)),
        fail_error="not a float"
    )
    HOUR = dict(
        test=lambda value: bool(re.search(r'^\d+$', value)) and (0 <= int(value) <= 23),
        fail_error="must be a value between 0 and 23",
        convert=lambda value: int(value)
    )


VALIDATORS = dict(
    allow_nsfw=Validator.BOOL,
    enabled=Validator.BOOL,
    enabled_resume=Validator.BOOL,
    frequency=dict(
        test=lambda value: value.lower() in ('day', 'week'),
        fail_error="must be either 'day' or 'week'",
        convert=lambda value: value.lower()
    ),
    hide_spoilers=Validator.BOOL,
    hour=Validator.HOUR,
    ignore_stickied=Validator.BOOL,
    ignore_if_newer_than=Validator.INT,
    limit=Validator.INT,
    max_frequency=Validator.INT,
    min_score=Validator.INT,
    min_upvote_perc=Validator.INT,
    number_of_posts=Validator.INT,
    quiet_hours_demultiplier=Validator.FLOAT,
    quiet_hours_end=Validator.HOUR,
    quiet_hours_start=Validator.HOUR,
    reddit_account=dict(
        test=lambda account_name: accounts.exist(account_name),
        fail_error="unknown account"
    ),
    send_medias=Validator.BOOL,
    sorting=dict(
        test=lambda value: value.lower() in ALL_SORTINGS,
        fail_error="unvalid sorting (not in: {})".format(', '.join(ALL_SORTINGS))
    ),
    test=Validator.BOOL,
    url_button=Validator.BOOL,
    comments_button=Validator.BOOL,
    webpage_preview=Validator.BOOL,
    weekday=dict(
        test=lambda value: bool(re.search(r'^\d+$', value)) and (0 <= int(value) <= 6),
        fail_error="must be a value between 0 and 6",
        convert=lambda value: int(value)
    ),
    youtube_download=Validator.BOOL,
    youtube_download_max_duration=Validator.INT
)


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

    if key not in VALIDATORS:
        logger.debug('"%s" key does not have a validator, applying standard conversions', key)
        value = standard_conversion(value)
    else:
        logger.debug('"%s" key must be validated', key)
        if not VALIDATORS[key]['test'](value):
            logger.debug('validation for key "%s" failed', key)
            error = 'This value for "{}" is not valid'.format(key)
            if VALIDATORS[key].get('fail_error', None):
                error = 'Value not valid: ' + VALIDATORS[key]['fail_error']
            update.message.reply_text(error)
            return

        logger.debug('validation: success')
        if VALIDATORS[key].get('convert', None):
            logger.debug('conversting value: %s', value)
            value = VALIDATORS[key]['convert'](value)

    logger.info('value after validation and conversion: %s', value)

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
