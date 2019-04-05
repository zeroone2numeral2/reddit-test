import re

STRING_TO_MINUTES_REGEX = re.compile(r'(?:(?P<hours>\d+)\s*h)?\s*(?:(?P<minutes>\d+)\s*m?)?$', re.I)


def dotted(number):
    return re.sub('(\d)(?=(\d{3})+(?!\d))', r'\1.', '{}'.format(number))


# print(dotted(1234546789))


def string_to_minutes(string):
    match = STRING_TO_MINUTES_REGEX.search(string)
    if match:
        hours, minutes = match.group('hours', 'minutes')
        sum = 0
        if hours:
            sum += int(hours) * 60
        if minutes:
            sum += int(minutes)

        return sum if sum > 0 else None
    else:
        return 'no match'


def pretty_seconds(n_seconds):
    if n_seconds < 60:
        return '{}s'.format(n_seconds)

    hours = int(n_seconds / 3600)
    minutes = int(n_seconds / 60) % 60
    seconds = n_seconds % 60

    string = ''
    if hours:
        string += '{}h '.format(hours)

    if minutes != 0 or (hours and seconds):
        string += '{}m '.format(minutes)

    if seconds or (minutes == 0 and hours == 0):
        string += '{}s'.format(seconds)

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


def main2():
    for string in strings:
        ret = string_to_minutes(string)
        print(string, '--', ret)



def main():
    test = [0, 60, 3600, 62, 3672, 3602]
    for t in test:
        print(t, '-->', pretty_seconds(t))




main()
