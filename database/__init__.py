from playhouse.sqlite_ext import SqliteExtDatabase

from config import config

db = SqliteExtDatabase(config.sqlite.filename, pragmas={'journal_mode': 'wal', 'foreign_keys': 0})


@db.func()
def day_part(dt_string):
    return int(dt_string[8:10])
