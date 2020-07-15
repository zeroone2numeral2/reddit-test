import logging
import argparse
import sys
import os

import peewee
from config import config

logging.basicConfig(format='[%(asctime)s][%(name)s] %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
parser = argparse.ArgumentParser()


def main(database_path):
    db = peewee.SqliteDatabase(database_path, pragmas={'journal_mode': 'wal'})

    db.execute_sql("""drop table resume_posts_tmp;""")

    db.execute_sql("""CREATE TABLE `resume_posts_tmp` (
    	`submission_id`	VARCHAR ( 255 ) NOT NULL,
    	`subreddit_id`	VARCHAR ( 255 ) NOT NULL,
    	`channel_id`	INTEGER NOT NULL,
    	`message_id`	INTEGER,
    	`posted_at`	DATETIME,
    	`sent_message`	VARCHAR ( 255 ),
    	`uploaded_bytes`	INTEGER
    );""")

    db.execute_sql("""
    insert into resume_posts_tmp
    select *
    from resume_posts;""")

    db.execute_sql("""drop table resume_posts;""")

    db.execute_sql("""CREATE TABLE `resume_posts` (
    	`submission_id`	VARCHAR ( 255 ) NOT NULL,
    	`subreddit_id`	VARCHAR ( 255 ) NOT NULL,
    	`channel_id`	INTEGER NOT NULL,
    	`message_id`	INTEGER,
    	`posted_at`	DATETIME,
    	`sent_message`	VARCHAR ( 255 ),
    	`uploaded_bytes`	INTEGER,
    	FOREIGN KEY(`channel_id`) REFERENCES `channels`(`channel_id`),
    	PRIMARY KEY(`submission_id`,`subreddit_id`),
    	FOREIGN KEY(`subreddit_id`) REFERENCES `subreddits`(`id`)
    );""")

    db.execute_sql("""insert into resume_posts
    select *
    from resume_posts_tmp;""")

    db.execute_sql("""drop table resume_posts_tmp;""")

    logger.info('<migration completed>')


if __name__ == '__main__':
    db_filepath = os.path.normpath(config.sqlite.filename)
    if not os.path.isfile(db_filepath):
        print('{} does not exist or is a directory'.format(db_filepath))
        sys.exit(1)

    main(db_filepath)
