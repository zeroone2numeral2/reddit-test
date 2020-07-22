from ..models import Channel


def get_channels():
    query = Channel.select()
    for channel in query:
        for subreddit in channel.subreddits.dicts():
            print(subreddit)
