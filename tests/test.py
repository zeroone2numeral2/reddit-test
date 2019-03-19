import praw
from pprint import pprint

reddit = praw.Reddit(client_id='0ri3963pR-qmog',
                     client_secret='aM5f4s7KyxaHoI3Y1sUkiSx5tjk',
                     user_agent='test script by -')


for submission in reddit.subreddit('anime').hot(limit=10):
    #"""
    print('submisson id:', submission.id)
    print('subreddit_ id:', submission.subreddit_id)
    print('subreddit: r/{}'.format(submission.subreddit))
    print('submission title:', submission.title)
    print('flair:', submission.link_flair_text)
    print('stickied:', submission.stickied)
    print('created at:', submission.created)
    print('created at (UTC):', submission.created_utc)
    print('from: u/{}'.format(submission.author))
    print('permalink:', 'https://reddit.com/{}'.format(submission.permalink))
    print('shortlink:', submission.shortlink)
    print('url:', submission.url)
    print('media:', submission.media)
    print('num_comments:', submission.num_comments)
    print('over_18:', submission.over_18)
    print('spoiler:', submission.spoiler)
    print('thumbnail:', submission.thumbnail)
    print('score:', submission.score)
    print('media:', submission.media)
    print('ups:', submission.ups, 'downs:', submission.downs)
    # print('text:', submission.selftext)
    try:
        if submission.spoiler:
            pprint('submission preview:', submission.preview)
        else:
            print(submission.preview)
    except AttributeError:
        print('No submission.preview')
    print()

    continue
    #"""

    for a in dir(submission):
        try:
            print('{}: '.format(a), getattr(submission, a))
        except:
            pass
