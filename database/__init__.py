import peewee

from config import config

db = peewee.SqliteDatabase(config.sqlite.filename, pragmas={'journal_mode': 'wal', 'foreign_keys': 0})
