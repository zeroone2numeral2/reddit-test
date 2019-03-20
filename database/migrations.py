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

    migrations = [
        [
            '20190318 pt. 1',
            migrator.add_column('subreddits', 'follow_quiet_hours', follow_quiet_hours),
            migrator.add_column('subreddits', 'limit', limit),
            migrator.add_column('subreddits', 'ignore_if_newer_then', ignore_if_newer_then)
        ],
        [
            '20190318 pt. 2 (rename ignore_if_newer_then to ignore_if_newer_than)',
            migrator.rename_column('subreddits', 'ignore_if_newer_then', 'ignore_if_newer_than')
        ],
        [
            '20190320 pt. 1 (add quiet_hours start/end)',
            migrator.add_column('subreddits', 'quiet_hours_start', quiet_hours_start),
            migrator.add_column('subreddits', 'quiet_hours_end', quiet_hours_end)
        ],
        [
            '20190320 pt. 2 (add allow_nsfw)',
            migrator.add_column('subreddits', 'allow_nsfw', allow_nsfw)
        ],
        [
            '20190320 pt. 3 (rename send_images to send_medias)',
            migrator.rename_column('subreddits', 'send_images', 'send_medias')
        ]
    ]

    print('Available migrations:')
    i = 0
    for migration in migrations:
        print('  {}. {}'.format(i, migration[0]))
        i += 1

    selected_key = ''
    while not re.search(r'^\d+$', selected_key):
        selected_key = input('Select a migration: ')
    
    if int(selected_key) > len(migrations) - 1:
        print('Bad index selected')
        sys.exit(1)

    migrations_list = migrations[int(selected_key)][1:]

    logger.info('Starting migration....')

    try:
        migrate(*migrations_list)
    except sqlite3.DatabaseError as e:
        print('database file {} is encrypted or is not a database'.format(db_filepath))
        print('sqlite3.DatabaseError:', str(e))
        sys.exit(1)
    except peewee.DatabaseError as e:
        print('peewee.DatabaseError:', str(e))
        sys.exit(1)
    except ValueError as e:
        print('ValueError:', str(e))
        sys.exit(1)

    logger.info('...migration completed')


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
