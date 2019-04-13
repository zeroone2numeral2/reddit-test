import re

STRING_TO_MINUTES_REGEX = re.compile(r'(?:(?P<hours>\d+)\s*h)?\s*(?:(?P<minutes>\d+)\s*m?)?$', re.I)


def dotted(number):
    return re.sub('(\d)(?=(\d{3})+(?!\d))', r'\1.', '{}'.format(number))


# print(dotted(1234546789))


def elapsed_time_smart(seconds):
    elapsed_minutes = seconds / 60
    elapsed_hours = elapsed_minutes / 60
    print(seconds, elapsed_minutes, elapsed_hours)

    # "n hours ago" if hours > 0, else "n minutes ago"
    if elapsed_hours >= 1:
        string = '{} hour'.format(int(elapsed_hours))
        if elapsed_hours >= 2:
            string += 's'
    else:
        string = '{} minute'.format(int(elapsed_minutes))
        if elapsed_minutes >= 2:
            string += 's'

    return string


strings = [
    '3h',
    '3 h 15 m',
    '1h2m',
    '3h',
    '120m',
    '123',
    'hm',
    'fcfg'
]



def main():
    test = [0, 57, 60, 578, 3600, 62, 3672, 3602]
    for t in test:
        print(elapsed_time_smart(t))
        print()




main()
