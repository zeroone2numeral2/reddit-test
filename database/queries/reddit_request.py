import datetime

from ..models import RedditRequest


def delete_old(days=14):
    query = RedditRequest.delete().where(RedditRequest.request_datetime_utc < (datetime.datetime.utcnow() - datetime.timedelta(days=days)))
    return query.execute()  # returns the number of deleted rows


def save_request(subreddit, account_name, client_name, dt=None):
    if not dt:
        dt = datetime.datetime.utcnow()

    reddit_request = RedditRequest(
        subreddit=subreddit,
        subreddit_name=subreddit.name,
        account_name=account_name,
        client_name=client_name,
        request_datetime_utc=dt
    )
    reddit_request.save()
