import logging
import argparse
import sys
import os

import peewee
import sqlite3
from playhouse.migrate import *

from const import *
from database.models import Style
from config import config

logging.basicConfig(format='[%(asctime)s][%(name)s] %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
parser = argparse.ArgumentParser()


def main(database_path):
    db = peewee.SqliteDatabase(database_path, pragmas={'journal_mode': 'wal'})

    migrator = SqliteMigrator(db)

    limit = peewee.IntegerField(null=True, default=25)
    ignore_if_newer_then = peewee.IntegerField(null=True)
    quiet_hours_start = peewee.IntegerField(null=True)
    quiet_hours_end = peewee.IntegerField(null=True)
    allow_nsfw = peewee.BooleanField(default=True, null=True)
    test = peewee.BooleanField(default=False)
    quiet_hours_demultiplier = peewee.IntegerField(null=True, default=0)
    enabled_resume = peewee.BooleanField(default=False)
    hour = peewee.IntegerField(default=22)
    weekday = peewee.IntegerField(default=5)
    frequency = peewee.CharField(default='day')
    number_of_posts = peewee.IntegerField(default=3)
    resume_template = peewee.CharField(null=True, default=DEFAULT_ANNOUNCEMENT_TEMPLATE)
    resume_last_posted_submission_dt = peewee.DateTimeField(null=True)
    posted_messages = peewee.IntegerField(null=True)
    invite_link = peewee.CharField(null=True)
    hide_spoilers = peewee.BooleanField(default=False, null=True)
    sent_message = peewee.CharField(null=True)
    medias_only = peewee.BooleanField(default=False, null=True)
    public = peewee.BooleanField(default=True)
    is_multireddit = peewee.BooleanField(default=False)
    multireddit_owner = peewee.CharField(null=True)
    youtube_download = peewee.BooleanField(default=False)
    youtube_download_max_duration = peewee.IntegerField(default=180)
    notified_on = peewee.DateTimeField(null=True)
    min_upvote_perc = peewee.IntegerField(null=True)
    uploaded_bytes = peewee.IntegerField(null=True)
    reddit_account = peewee.CharField(null=True)
    reddit_client = peewee.CharField(null=True)
    ignore_flairless = peewee.BooleanField(default=False, null=True)
    style = peewee.ForeignKeyField(Style, backref='subreddit', on_delete='NO ACTION', null=True)
    template_resume = peewee.CharField(null=True)
    template_caption = peewee.CharField(null=True)
    default = peewee.BooleanField(default=False)
    template_override = peewee.CharField(null=True)

    migrations = [
        # 20190318 pt. 1
        migrator.add_column('subreddits', 'limit', limit),
        migrator.add_column('subreddits', 'ignore_if_newer_then', ignore_if_newer_then),
        # 20190318 pt. 2 (rename ignore_if_newer_then to ignore_if_newer_than)
        migrator.rename_column('subreddits', 'ignore_if_newer_then', 'ignore_if_newer_than'),
        # 20190320 pt. 1 (add quiet_hours start/end)
        migrator.add_column('subreddits', 'quiet_hours_start', quiet_hours_start),
        migrator.add_column('subreddits', 'quiet_hours_end', quiet_hours_end),
        # 20190320 pt. 2 (add allow_nsfw)
        migrator.add_column('subreddits', 'allow_nsfw', allow_nsfw),
        # 20190320 pt. 3 (rename send_images to send_medias)
        migrator.rename_column('subreddits', 'send_images', 'send_medias'),
        # 20190321 (add test to Subreddit)
        migrator.add_column('subreddits', 'test', test),
        # 20190327 (add quiet_hours_demultiplier to Subreddit)
        migrator.add_column('subreddits', 'quiet_hours_demultiplier', quiet_hours_demultiplier),
        # 20190402 (resume job)
        migrator.add_column('subreddits', 'enabled_resume', enabled_resume),
        migrator.add_column('subreddits', 'hour', hour),
        migrator.add_column('subreddits', 'weekday', weekday),
        migrator.add_column('subreddits', 'frequency', frequency),
        migrator.add_column('subreddits', 'number_of_posts', number_of_posts),
        migrator.add_column('subreddits', 'resume_template', resume_template),
        # 20190404 (resume_last_posted_submission_dt)
        migrator.add_column('subreddits', 'resume_last_posted_submission_dt', resume_last_posted_submission_dt),
        # 20190411 (drop not null)
        migrator.drop_not_null('subreddits', 'template_matrix'),
        # 20190430
        migrator.drop_column('subreddits', 'follow_quiet_hours'),
        migrator.drop_column('subreddits', 'images_only'),
        migrator.drop_column('subreddits', 'images_as_file'),
        migrator.drop_column('subreddits', 'enabled_matrix'),
        migrator.drop_column('subreddits', 'template_matrix'),
        migrator.drop_column('subreddits', 'room_id'),
        # 20190508
        migrator.add_column('jobs', 'posted_messages', posted_messages),
        # 20190513
        migrator.add_column('channels', 'invite_link', invite_link),
        # 20190520
        migrator.add_column('subreddits', 'hide_spoilers', hide_spoilers),
        # 20190826
        migrator.add_column('posts', 'sent_message', sent_message),
        migrator.add_column('resume_posts', 'sent_message', sent_message),
        # 20190830
        migrator.add_column('subreddits', 'medias_only', medias_only),
        # 20190909
        migrator.add_column('channels', 'public', public),
        # 20190923
        migrator.add_column('subreddits', 'is_multireddit', is_multireddit),
        migrator.add_column('subreddits', 'multireddit_owner', multireddit_owner),
        # 20200428
        migrator.drop_not_null('subreddits', 'channel_id'),
        # 20200513
        migrator.add_column('subreddits', 'youtube_download', youtube_download),
        migrator.add_column('subreddits', 'youtube_download_max_duration', youtube_download_max_duration),
        # 20200520
        migrator.add_column('channels', 'notified_on', notified_on),
        # 20200617
        migrator.add_column('subreddits', 'min_upvote_perc', min_upvote_perc),
        # 20200618
        migrator.add_column('jobs', 'uploaded_bytes', uploaded_bytes),
        migrator.add_column('posts', 'uploaded_bytes', uploaded_bytes),
        migrator.add_column('resume_posts', 'uploaded_bytes', uploaded_bytes),
        # 20200619
        migrator.add_column('subreddits', 'reddit_account', reddit_account),
        migrator.add_column('subreddits', 'reddit_client', reddit_client),
        # 20200714 ignore_flairless
        migrator.add_column('subreddits', 'ignore_flairless', ignore_flairless),
        # 20200715
        migrator.add_column('subreddits', 'style', style),
        migrator.add_column('subreddits', 'style_id', peewee.IntegerField(null=True)),  # workaround, line above doesn't work
        migrator.add_column('styles', 'template_resume', template_resume),
        migrator.add_column('styles', 'template_caption', template_caption),
        migrator.add_column('styles', 'default', default),
        migrator.drop_column('subreddits', 'template_resume'),
        migrator.drop_column('subreddits', 'template'),
        migrator.drop_column('subreddits', 'template_no_url'),
        migrator.drop_column('subreddits', 'url_button'),
        migrator.drop_column('subreddits', 'url_button_template'),
        migrator.drop_column('subreddits', 'comments_button'),
        migrator.drop_column('subreddits', 'comments_button_template'),
        migrator.drop_column('subreddits', 'send_medias'),
        migrator.drop_column('subreddits', 'webpage_preview'),
        # 20200716
        migrator.add_column('subreddits', 'template_override', template_override),
    ]

    logger.info('Starting migration....')
    for migration in migrations:
        try:
            logger.info('executing single migration...')
            migrate(migration)
            logger.info('...single migration executed')
        except sqlite3.DatabaseError as e:
            print('database file {} is encrypted or is not a database'.format(database_path))
            print('sqlite3.DatabaseError:', str(e))
            sys.exit(1)
        except peewee.DatabaseError as e:
            logger.info('peewee.DatabaseError: %s', str(e))
            continue
        except ValueError as e:
            logger.info('ValueError: %s', str(e))
            continue

    logger.info('<migration completed>')


if __name__ == '__main__':
    db_filepath = os.path.normpath(config.sqlite.filename)
    if not os.path.isfile(db_filepath):
        print('{} does not exist or is a directory'.format(db_filepath))
        sys.exit(1)

    main(db_filepath)
