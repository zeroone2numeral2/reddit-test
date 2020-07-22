import datetime

import peewee
from pytz import FixedOffset

from database import db


class Job(peewee.Model):
    id = peewee.IntegerField(primary_key=True)
    name = peewee.CharField(null=False)
    start = peewee.DateTimeField(null=True)  # https://github.com/coleifer/peewee/issues/1427
    end = peewee.DateTimeField(null=True)  # https://github.com/coleifer/peewee/issues/1427
    duration = peewee.IntegerField(null=True)
    posted_messages = peewee.IntegerField(null=True)
    uploaded_bytes = peewee.IntegerField(null=True)
    result = peewee.CharField(null=True)

    class Meta:
        table_name = 'jobs'
        database = db

    def __repr__(self):
        return '<Job row {}: {}>'.format(self.id, self.name)

    @property
    def start_dt(self) -> [datetime.datetime, None]:
        if not isinstance(self.start, str):
            return self.start

        return self.convert_to_datetime(self.start)

    @property
    def end_dt(self) -> [datetime.datetime, None]:
        if not isinstance(self.end, str):
            return self.end

        return self.convert_to_datetime(self.end)

    @staticmethod
    def convert_to_datetime(value):
        datetime_str, zone = value[:-6], value[-6:]  # value.rsplit('+', 1)  # Expected YYYY-mm-dd HH:MM:SS.ffffff-ZH:ZM

        val = datetime.datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S.%f')

        if zone.startswith('-'):
            mult = -1
            zone = zone[1:]
        else:
            mult = 1

        zh, zm = int(zone[:2]), int(zone[-2:])
        offset = FixedOffset(mult * (zh * 60 + zm))

        return val.replace(tzinfo=offset)

    @classmethod
    def durations(cls, top=100, job_name='%'):
        job_name = job_name or '%'
        rows = cls.select().where(cls.name ** job_name).order_by(cls.id.desc())

        if not rows:
            return None

        result = list()
        for job in rows[:top]:
            result.append((job.name, job.start_dt, job.duration, job.posted_messages, job.uploaded_bytes))

        return result

    @classmethod
    def last_job(cls, job_name='%'):
        job_name = job_name or '%'
        rows = cls.select().where(cls.name ** job_name).order_by(cls.id.desc()).limit(1)

        if not rows:
            return None

        return rows[0]

    @classmethod
    def delete_old(cls, days=31):
        query = cls.delete().where(cls.start < (datetime.datetime.utcnow() - datetime.timedelta(days=days)))
        return query.execute()  # returns the number of deleted rows
