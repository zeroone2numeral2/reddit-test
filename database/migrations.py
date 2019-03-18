import logging
import argparse
import sys
import os

import peewee
import sqlite3
from playhouse.migrate import *

logging.basicConfig(format='[%(asctime)s][%(name)s] %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
parser = argparse.ArgumentParser()


def main(db_filepath):
    db = peewee.SqliteDatabase(db_filepath, pragmas={'journal_mode': 'wal'})

    migrator = SqliteMigrator(db)

    follow_quiet_hours = peewee.BooleanField(null=True, default=True)
    limit = peewee.IntegerField(null=True, default=25)
    ignore_if_newer_then = peewee.IntegerField(null=True)

    logger.info('Starting migration....')

    try:
        migrate(
            # 18/03/2019 pt. 1
            migrator.add_column('subreddits', 'follow_quiet_hours', follow_quiet_hours),
            migrator.add_column('subreddits', 'limit', limit),
            migrator.add_column('subreddits', 'ignore_if_newer_then', ignore_if_newer_then),
            # 18/03/2019 pt. 2
            migrator.rename_column('subreddits', 'ignore_if_newer_then', 'ignore_if_newer_than'),
        )
    except (peewee.DatabaseError, sqlite3.DatabaseError):
        print('database file {} is encrypted or is not a database'.format(db_filepath))
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
