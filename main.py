from os import path

from classes import Feed, Message


USER = 'Mike'
EMAIL_ADDRESS = 'pgmike@gmail.com'
DATABASE = path.join(path.dirname(__file__), 'data.db')
DICT_FILE = path.join(path.dirname(__file__), 'feed_dict.p')
URL = 'https://denver.craigslist.org/search/cta?format=rss&bundleDuplicates=1&' \
      'searchNearby=1&min_auto_year=2015&max_auto_miles=30000&auto_make_model=' \
      'GTI&max_price=20000&auto_transmission=1&search_distance=150&postal=80013'


def main():
    with Feed(URL, DICT_FILE) as feed:
        new_items = feed.refresh_feed()
    if new_items is not None:
        Message(USER, EMAIL_ADDRESS, new_items)


if __name__ == '__main__':
    main()
