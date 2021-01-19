from ..models import Channel


def get_channels():
    query = Channel.select()
    return list(query)
