import logging
import argparse
import sys
import os
import re

import peewee
import sqlite3
from playhouse.migrate import *

logging.basicConfig(format='[%(asctime)s][%(name)s] %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
parser = argparse.ArgumentParser()

MIGRATIONS = list(
    (
        '20191803pt1',
    )
)


def main(db_filepath):
    db = peewee.SqliteDatabase(db_filepath, pragmas={'journal_mode': 'wal'})

    migrator = SqliteMigrator(db)

    follow_quiet_hours = peewee.BooleanField(null=True, default=True)
    limit = peewee.IntegerField(null=True, default=25)
    ignore_if_newer_then = peewee.IntegerField(null=True)
    quiet_hours_start = peewee.IntegerField(null=True)
    quiet_hours_end = peewee.IntegerField(null=True)
    allow_nsfw = peewee.BooleanField(default=True, null=True)
    test = peewee.BooleanField(default=False)
    quiet_hours_demultiplier = peewee.IntegerField(null=True, default=0)
    enabled_resume = peewee.BooleanField(default=False)
    hour = peewee.IntegerField(default=22)
    frequency = peewee.CharField(default='day')
    number_of_posts = peewee.IntegerField(default=3)
    resume_template = peewee.CharField(null=True)

    migrations = [
        # 20190318 pt. 1
        migrator.add_column('subreddits', 'follow_quiet_hours', follow_quiet_hours),
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
        migrator.add_column('subreddits', 'frequency', frequency),
        migrator.add_column('subreddits', 'number_of_posts', number_of_posts),
        migrator.add_column('subreddits', 'resume_template', resume_template)
    ]

    logger.info('Starting migration....')
    for migration in migrations:
        try:
            logger.info('executing single migration...')
            migrate(migration)
            logger.info('...single migration executed')
        except sqlite3.DatabaseError as e:
            print('database file {} is encrypted or is not a database'.format(db_filepath))
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
    parser.add_argument('-db', '--database', action='store', help='Database file path')

    args = parser.parse_args()
    if not args.database:
        print('pass a db filename using the -db [file path] argument')
        sys.exit(1)

    db_filepath = os.path.normpath(args.database)
    if not os.path.isfile(db_filepath):
        print('{} does not exist or is a directory'.format(db_filepath))
        sys.exit(1)

    main(db_filepath)
