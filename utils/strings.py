import re


def find_urls(string):
    # findall() has been used
    # with valid conditions for urls in string
    url = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', string)
    return url


def get_trailing_number(s):
    m = re.search(r'\d*\.\d+|\d+$', s)
    if not m:
        m = re.search(r'\d+$', s)
        if m:
            return int(m.group())

    else:
        return float(m.group())

    return None


def get_trailing_float(s):
    return float(m.group()) if m else None


def replace_count_reverse(source, target, replacement, count):
    li = source.rsplit(target, count)
    return replacement.join(li)
