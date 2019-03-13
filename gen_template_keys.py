from reddit import Sender
from reddit import reddit


def main():
    print('getting one submission...')
    for submission in reddit.subreddit('all').hot(limit=1):
        sender = Sender(None, None, None, submission)

        with open('template_keys.txt', 'w+') as f:
            print('writing file...')
            f.write('\n'.join(sender.template_keys))


if __name__ == '__main__':
    main()
