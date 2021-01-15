
from math import floor


def main():
    def elapsed_smart_compact(seconds):
        if seconds < 1:
            return '{}s'.format(seconds)

        string = ''

        days = seconds // (3600 * 24)
        seconds %= 3600 * 24
        print('', 'days', days, 'seconds', seconds)
        if days:
            string += '{}d'.format(days)

        hours = seconds // 3600
        seconds %= 3600
        print('', 'hours', hours, 'seconds', seconds)
        if hours:
            string += '{}h'.format(hours)

        minutes = seconds // 60
        seconds %= 60
        print('', 'minutes', minutes, 'seconds', seconds)
        if minutes:
            string += '{}m'.format(minutes)

        return string

    print(elapsed_smart_compact(2 * 60))
    print(elapsed_smart_compact(61 * 60))
    print(elapsed_smart_compact(2981 * 60))


if __name__ == '__main__':
    main()
