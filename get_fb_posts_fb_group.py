import json
import datetime
import csv
import time
import re
try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request


# input date formatted as YYYY-MM-DD
since_date = ""
until_date = ""

from secret import *

access_token = app_id + "|" + app_secret


def request_until_succeed(url):
    req = Request(url)
    success = False
    while success is False:
        try:
            response = urlopen(req)
            if response.getcode() == 200:
                success = True
        except Exception as e:
            print(e)
            time.sleep(5)

            print("Error for URL {}: {}".format(url, datetime.datetime.now()))
            print("Retrying.")

    return response.read()


# Needed to write tricky unicode correctly to csv

def unicode_decode(text):
    try:
        return text.encode('utf-8').decode()
    except UnicodeDecodeError:
        return text.encode('utf-8')


def getFacebookPageFeedUrl(base_url):

    # Construct the URL string; see http://stackoverflow.com/a/37239851 for
    # Reactions parameters
    fields = "&fields=message,created_time,id"
    url = base_url + fields

    return url


def processFacebookPageFeedStatus(status):

    # The status is now a Python dictionary, so for top-level items,
    # we can simply call the key.

    # Additionally, some items may not always exist,
    # so must check for existence first

    status_id = status['id']

    status_message = '' if 'message' not in status else \
        unicode_decode(status['message'])

    # Time needs special care since a) it's in UTC and
    # b) it's not easy to use in statistical programs.

    status_published = datetime.datetime.strptime(
        status['created_time'], '%Y-%m-%dT%H:%M:%S+0000')
    status_published = status_published + \
        datetime.timedelta(hours=-5)  # EST
    status_published = status_published.strftime(
        '%Y-%m-%d %H:%M:%S')  # best time format for spreadsheet programs

    return (status_id, status_message, status_published)


def scrapeFacebookPageFeedStatus(group_id, access_token, since_date, until_date):
    with open('{}_facebook_statuses.csv'.format(group_id), 'w') as file:
        w = csv.writer(file)
        w.writerow(["status_id", "status_message", "status_published"])

        has_next_page = True
        num_processed = 0   # keep a count on how many we've processed
        scrape_starttime = datetime.datetime.now()

        # /feed endpoint pagenates througn an `until` and `paging` parameters
        until = ''
        paging = ''
        base = "https://graph.facebook.com/v2.9"
        node = "/{}/feed".format(group_id)
        parameters = "/?limit={}&access_token={}".format(100, access_token)
        since = "&since={}".format(since_date) if since_date \
            is not '' else ''
        until = "&until={}".format(until_date) if until_date \
            is not '' else ''

        print("Scraping {} Facebook Group: {}\n".format(
            group_id, scrape_starttime))

        while has_next_page:
            until = '' if until is '' else "&until={}".format(until)
            paging = '' if until is '' else "&__paging_token={}".format(paging)
            base_url = base + node + parameters + since + until + paging

            url = getFacebookPageFeedUrl(base_url)
            statuses = json.loads(request_until_succeed(url))

            for status in statuses['data']:

                # Ensure it is a status with the expected metadata
                if 'message' in status:
                    status_data = processFacebookPageFeedStatus(status)

                # output progress occasionally to make sure code is not
                # stalling
                num_processed += 1
                if num_processed % 100 == 0:
                    print("{} Statuses Processed: {}".format
                          (num_processed, datetime.datetime.now()))

            # if there is no next page, we're done.
            if 'paging' in statuses:
                next_url = statuses['paging']['next']
                until = re.search('until=([0-9]*?)(&|$)', next_url).group(1)
                paging = re.search(
                    '__paging_token=(.*?)(&|$)', next_url).group(1)

            else:
                has_next_page = False

        print("\nDone!\n{} Statuses Processed in {}".format(
              num_processed, datetime.datetime.now() - scrape_starttime))


if __name__ == '__main__':
    scrapeFacebookPageFeedStatus(group_id, access_token, since_date, until_date)


# The CSV can be opened in all major statistical programs. Have fun! :)
