import re


def find_urls(string):
    # findall() has been used
    # with valid conditions for urls in string
    url = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', string)
    return url


def get_trailing_number(s):
    m = re.search(r'\d+$', s)
    return int(m.group()) if m else None
