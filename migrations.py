import logging
import argparse
import sys
import os

import peewee
import sqlite3
from playhouse.migrate import *

from const import *
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
        # 20190410 (rename resume_template to template_resume)
        migrator.rename_column('subreddits', 'resume_template', 'template_resume'),
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
