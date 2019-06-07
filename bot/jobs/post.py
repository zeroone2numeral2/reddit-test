import logging
from logging.handlers import RotatingFileHandler
import time
import os

from telegram import ParseMode
from telegram.error import BadRequest
from telegram.error import TelegramError
from ptbplugins.jobregistration import RUNNERS
from ptbplugins import Jobs

from utilities import u
from utilities import d
from utilities import l
from database.models import Subreddit
from database.models import Post
from database import db
from reddit import reddit
from reddit import Sender
from config import config

logger = logging.getLogger('sp')

NOT_VALUES = (None, False)


def update_logger_file(subreddit_name=None):
    file_name = '{}.log'.format(subreddit_name if subreddit_name else 'redditmirror')
    file_path = os.path.join('logs', file_name)

    rfhandler = RotatingFileHandler(file_path, maxBytes=1048576, backupCount=500)
    formatter = logging.Formatter('[%(asctime)s][%(name)s:%(lineno)d][%(levelname)s] >>> %(message)s')
    rfhandler.setFormatter(formatter)
    rfhandler.setLevel(logging.DEBUG)

    logger.handlers = [rfhandler]


def its_quiet_hours(subreddit: Subreddit):
    now = u.now()

    if subreddit.quiet_hours_start not in NOT_VALUES and subreddit.quiet_hours_end not in NOT_VALUES:
        logger.info('subreddit has quiet hours (start/end: %d -> %d)', subreddit.quiet_hours_start,
                    subreddit.quiet_hours_end)
        if subreddit.quiet_hours_start >= subreddit.quiet_hours_end:
            if now.hour >= subreddit.quiet_hours_start or now.hour <= subreddit.quiet_hours_end:
                logger.info('we are in the quiet hours timeframe (now: %d), ignoring...', now.hour)
                return True
        elif subreddit.quiet_hours_start < subreddit.quiet_hours_end:
            if subreddit.quiet_hours_start <= now.hour <= subreddit.quiet_hours_end:
                logger.info('we are in the quiet hours timeframe (now: %d), ignoring...', now.hour)
                return True
        else:
            logger.info('we are not in the quiet hours timeframe (hour: %d)', now.hour)
            return False
    else:
        # if the subreddit doesn't have the quiet hours configured, we use the config ones
        if now.hour >= config.quiet_hours.start or now.hour <= config.quiet_hours.end:
            logger.info('quiet hours (%d - %d UTC): do not do anything (current hour UTC: %d)',
                        config.quiet_hours.start, config.quiet_hours.end, now.hour)
            return True
        else:
            return False


def calculate_quiet_hours_demultiplier(subreddit: Subreddit):
    if subreddit.quiet_hours_demultiplier is None:
        subreddit.quiet_hours_demultiplier = 0
        subreddit.save()

    if subreddit.quiet_hours_demultiplier == 1:
        # if the multiplier is 1, no need to do other checks, the frequency is the same during quiet hours
        logger.info('subreddit quiet hours demultiplier is 1: posts frequency is unchanged, no need to check if we are in quiet hours')
        return 1
    elif its_quiet_hours(subreddit):
        # if it's quiet hours: return the demultiplier
        return subreddit.quiet_hours_demultiplier
    else:
        logger.info('we are not into the quiet hours timeframe: frequency multiplier is 1')
        return 1


def time_to_post(subreddit: Subreddit, quiet_hours_demultiplier):
    # we increase the max_frequency of the value set for the subreddit, so we can decrease the posting frequency
    # during quiet hours. If we are not in the quiet hours timeframe, the multplier will always be one,
    # so the max_frequency will be the same
    calculated_max_frequency = int(subreddit.max_frequency * quiet_hours_demultiplier)

    now = u.now()
    now_string = u.now(string=True)

    if subreddit.last_posted_submission_dt:
        logger.info(
            'elapsed time (now -- last post): %s -- %s',
            now_string,
            subreddit.last_posted_submission_dt.strftime('%d/%m/%Y %H:%M')
        )
        elapsed_time_minutes = (now - subreddit.last_posted_submission_dt).total_seconds() / 60
    else:
        logger.info('(elapsed time cannot be calculated: no last submission datetime for the subreddit)')
        elapsed_time_minutes = 9999999

    if subreddit.last_posted_submission_dt and elapsed_time_minutes < calculated_max_frequency:
        logger.info(
            'elapsed time is lower than max_frequency (%d*%d minutes), continuing to next subreddit...',
            subreddit.max_frequency,
            quiet_hours_demultiplier
        )
        return False
    else:
        return True


def process_submissions(subreddit: Subreddit):
    logger.info('fetching submissions (sorting: %s)', subreddit.sorting)

    limit = subreddit.limit or config.praw.submissions_limit
    for submission in reddit.iter_submissions(subreddit.name, subreddit.sorting.lower(), limit=limit):
        logger.info('checking submission: %s (%s...)...', submission.id, submission.title[:64])
        if Post.already_posted(subreddit, submission.id):
            logger.info('...submission %s has already been posted', submission.id)
            continue
        else:
            logger.info('...submission %s has NOT been posted yet, we will post this one if it passes checks',
                        submission.id)

            yield submission


def process_subreddit(subreddit: Subreddit, bot):
    logger.info('processing subreddit: %s (r/%s)', subreddit.subreddit_id, subreddit.name)

    quiet_hours_demultiplier = calculate_quiet_hours_demultiplier(subreddit)
    if quiet_hours_demultiplier == 0:  # 0: do not post anything if we are in the quiet hours timeframe
        logger.info('quiet hours demultiplier of r/%s is 0: skipping posting during quiet hours', subreddit.name)
        return 0

    if not time_to_post(subreddit, quiet_hours_demultiplier):
        return 0

    senders = list()
    for submission in process_submissions(subreddit):
        sender = Sender(bot, subreddit, submission)
        if sender.test_filters():
            logger.info('submission %s ("%s") passed filters', submission.id, submission.title[:12])
            senders.append(sender)
            if len(senders) >= subreddit.number_of_posts:
                logger.info('we collected enough posts to post (number_of_posts: %d)', subreddit.number_of_posts)
                break
        else:
            # no need to save ignored submissions in the database, because the next time
            # they might pass the filters
            # sender.register_ignored()
            logger.info('submission di NOT pass filters, continuing to next one...')
            sender = None  # avoid to use a Sender that did not pass the filters
            continue

    if not senders:
        logger.info('no (valid) submission returned for r/%s, continuing to next subreddit/channel...', subreddit.name)
        return 0

    logger.info('we collected %d/%d submissions to post', len(senders), subreddit.number_of_posts)

    messages_posted = 0
    for sender in senders:
        logger.info('submission url: %s', sender.submission.url)
        logger.info('submission title: %s', sender.submission.title)

        try:
            time.sleep(config.jobs.posts_cooldown)  # sleep some seconds before posting
            sent_message = sender.post()
        except (BadRequest, TelegramError) as e:
            logger.error('Telegram error while posting the message: %s', str(e), exc_info=True)
            continue
        except Exception as e:
            logger.error('generic error while posting the message: %s', str(e), exc_info=True)
            continue

        if sent_message:
            if not subreddit.test:
                logger.info('creating Post row...')
                sender.register_post()

                logger.info('updating Subreddit last post datetime...')
                subreddit.last_posted_submission_dt = u.now()
                subreddit.save()
            else:
                logger.info('not creating Post row and not updating last submission datetime: r/%s is a testing subreddit', subreddit.name)

            messages_posted += 1  # we posted one message
        else:
            logger.warning('Sender.post() did not return any sent message, so we are not registering this submission and the last post datetime')

        # time.sleep(1)

    return messages_posted


@Jobs.add(RUNNERS.run_repeating, interval=config.jobs.posts_job.interval * 60, first=config.jobs.posts_job.first * 60, name='posts_job')
@d.logerrors
@d.log_start_end_dt
@db.atomic('IMMEDIATE')
def check_posts(bot, _):
    subreddits = (
        Subreddit.select()
        .where(Subreddit.enabled == True)
    )

    total_posted_messages = 0
    for subreddit in subreddits:
        try:
            # l.set_logger_file('subredditprocessor', subreddit.name)
            posted_messages = process_subreddit(subreddit, bot)
            # l.set_logger_file('subredditprocessor')

            total_posted_messages += int(posted_messages)
        except Exception as e:
            logger.error('error while processing subreddit r/%s: %s', subreddit.name, str(e), exc_info=True)
            text = '#mirrorbot_error - {} - <code>{}</code>'.format(subreddit.name, u.escape(str(e)))
            bot.send_message(config.telegram.log, text, parse_mode=ParseMode.HTML)

        # time.sleep(1)

    return total_posted_messages
