import datetime
import logging
import requests
import sys
from collections import defaultdict
from HTMLParser import HTMLParser

logger = logging.getLogger(__name__)

def setup_logging():
    handler = logging.StreamHandler(stream=sys.stdout)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

class FoodDaysWikiParser(HTMLParser):
    def __init__(self, res):
        HTMLParser.__init__(self)
        self.us = False
        self.month = None
        self.tr = False
        self.td = 0
        self.row = defaultdict(list)
        self.res = res

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id') == 'United_States':
            self.us = True
        if self.us:
            if tag == 'h2':
                self.us = False
            elif tag == 'span' and a.get('id') is not None:
                self.month = a.get('id')
            elif tag == 'tr':
                self.tr = True
            elif tag == 'td':
                self.td += 1

    def handle_endtag(self, tag):
        if tag == 'tr' and self.tr:
            day = ' '.join(filter(None, self.row[1]))
            event = ' '.join(filter(None, self.row[2]))
            self.res[(self.month, day)] = event
            self.row = defaultdict(list)
            self.td = 0
            self.tr = False

    def handle_data(self, data):
        if self.us and self.tr:
            self.row[self.td].extend(data.strip().split(' '))

def handle_non_dates(day, month, year):
    nums = {
        'First': 1,
        'Second': 2,
        'Third': 3,
        'Fourth': 4,
    }
    weekdays = {
        'Monday': 1,
        'Tuesday': 2,
        'Wednesday': 3,
        'Thursday': 4,
        'Friday': 5,
        'Saturday': 6,
        'Sunday': 7,
    }
    months = {
        'January': 1,
        'February': 2,
        'March': 3,
        'April': 4,
        'May': 5,
        'June': 6, 
        'July': 7, 
        'August': 8,
        'September': 9,
        'October': 10,
        'November': 11,
        'December': 12,
    }
    first = day.split(' ')[0] 
    f = nums.get(first)
    second = day.split(' ')[1]
    s = weekdays.get(second)
    m = months.get(month)
    # TODO: handle things of the form "Last X" or "Day After"

    if f and s:
        # Go through every date and check if it's the `s` weekday equaling `f`
        counter = 0
        for day_num in xrange(1, 32):
            try:
                d = datetime.date(year, m, day_num)
                if d.isoweekday() == s:
                    counter += 1
                    if counter == f:
                        return d
            except Exception as e:
                logger.debug('Encountered exception %s when trying to find %s' % (e, day))
    else:
        logger.debug('Dont know how to parse %s' % day)
    logger.debug('Couldnt return anything :(')

def parseDay(day, month, year):
    """
    day is the thing to parse. month and year are the context for the day
    ie 'First Monday' could be the day and the context is that it's in
    the month of Feburary of 2016.
    """
    try:
        d = datetime.datetime.strptime(day, '%B %d')
        d = d.replace(year=year)
        d = d.date()
        return d
    except ValueError as ve:
        # This happens for things like February 29, which only happens on certain years
        if ve.message == 'day is out of range for month':
            logger.debug('%s %s is out of range' % (day, year))
            return None
        else:
            return handle_non_dates(day, month, year)

def build_days(url, year):
    resp = requests.get(url)
    result = {}
    h = FoodDaysWikiParser(result)
    h.feed(resp.text)

    # Remove things in result that are a result of parsing headers to tables
    to_del = []
    for (month, day), _ in result.iteritems():
        if day == '':
            to_del.append((month, day))
    for el in to_del:
        del result[el]

    new_result = {}
    for (month, day), event in result.iteritems():
        d = parseDay(day, month, year)
        if d:
            new_result[d] = event
    return new_result

def main():
    today = datetime.date.today()
    year = today.year
    url = 'https://en.wikipedia.org/wiki/List_of_food_days'
    days = build_days(url, year)
    today_disp = today.isoformat()
    if today in days:
        print '%s: Time to pig out! Today is %s.' % (today_disp, days[today])
    else:
        print '%s: Sorry, nothing is happening today.' % today_disp

if __name__ == '__main__':
    setup_logging()
    main()
