from playhouse.sqlite_ext import SqliteExtDatabase

from config import config

# we disable foreign keys costraint for now, as the database FK costraint are kinda messed up, and to fix them
# we have to create the database again (since FK costraint (ON DELETE and so on) are set during tables creation
# and can't be updated afterwards
# for reference: https://stackoverflow.com/q/1884818/13350541
db = SqliteExtDatabase(config.sqlite.filename, pragmas={'journal_mode': 'wal', 'foreign_keys': 0})


@db.func()
def day_part(dt_string):
    return int(dt_string[8:10])
