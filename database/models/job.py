import peewee

from database import db


class Job(peewee.Model):
    id = peewee.IntegerField(primary_key=True)
    name = peewee.CharField(null=False)
    start = peewee.DateTimeField(null=True)
    end = peewee.DateTimeField(null=True)
    duration = peewee.IntegerField(null=True)
    posted_messages = peewee.IntegerField(null=True)
    result = peewee.CharField(null=True)

    class Meta:
        table_name = 'jobs'
        database = db

    def __repr__(self):
        return '<Job row {}: {}>'.format(self.id, self.name)

    @classmethod
    def durations(cls, top=100, job_name='%'):
        job_name = job_name or '%'
        rows = cls.select().where(cls.name ** job_name).order_by(cls.id.desc())

        if not rows:
            return None

        result = list()
        for job in rows[:top]:
            result.append((job.name, job.start, job.duration, job.posted_messages))

        return result

