from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os import listdir, path
import pickle
import smtplib
import sqlite3

import feedparser as fp
from jinja2 import Environment, PackageLoader, select_autoescape

from config import Config


class Database:
    def __init__(self, database):
        """
        :param database: string, path to sqlite db file
        """
        self.database = database
        self.conn = sqlite3.connect(self.database)
        self.c = self.conn.cursor()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()
        del self

    def __repr__(self):
        return f'Database("{self.database}")'

    def __str__(self):
        return f'Database instantiated using {self.database} file'

    @property
    def cursor(self):
        return self.c

    @staticmethod
    def init_database(database):
        if database not in listdir(path.dirname(database)):
            with Database(database) as db:
                c = db.cursor
                c.execute('CREATE TABLE IF NOT EXISTS posts '
                          '(id INTEGER,'
                          'notification_status BOOLEAN,'
                          'url text)')

    def insert_entry(self, id_num, url):
        self.c.execute('INSERT INTO posts VALUES (?,?,?)',
                       (id_num, False, url),)


class Feed:
    def __init__(self, url, dict_file):
        """
        :param url: string, RSS feed URL
        :param dict_file: string, path to a pickled dict file.
        """
        self.url = url
        self.dict_file = dict_file
        self.feed_dict = self.load_dict()

    def __repr__(self):
        return f'Feed({self.url})'

    def __str__(self):
        return f'Feed object using {self.url}'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def load_dict(self):
        files = [path.join(path.dirname(__file__), item) for item in
                 listdir(path.dirname(__file__))]
        if self.dict_file not in files:
            return {}
        else:
            with open(self.dict_file, 'rb') as file:
                return pickle.load(file)

    def save_dict(self):
        with open(self.dict_file, 'wb') as file:
            pickle.dump(self.feed_dict, file)

    def refresh_feed(self):
        new_items = []
        listings = fp.parse(self.url)['entries']
        for listing in listings:
            if listing['id'] not in self.feed_dict:
                if '&#x0024;' in listing['title']:
                    listing['title'] = listing['title'].replace('&#x0024;', '$')
                if '&#x0024;' in listing['summary']:
                    listing['summary'] = listing['summary'].replace('&#x0024;', '$')
                self.feed_dict[listing['id']] = listing
                new_items.append(listing)
        self.save_dict()
        if len(new_items) > 0:
            return new_items
        else:
            return None


class Message:

    def __init__(self, user, email_address, listings):
        """
        :param user: user's name
        :param email_address: string
        :param listings: list of dicts of CL postings
        """
        self.user = user
        self.email_address = email_address
        self.listings = listings
        self.text_message = self.render_text()
        self.html_message = self.render_html()
        self.send_email()

    def __repr__(self):
        return f'Message({self.email_address})'

    def __str__(self):
        return f'Message object'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def render_html(self):
        env = Environment(
            loader=PackageLoader('classes', 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        template = env.get_template('base.html')
        render = template.render(user=self.user, listings=self.listings)
        return render

    def render_text(self):
        env = Environment(
            loader=PackageLoader('classes', 'templates'),
            autoescape=select_autoescape(['.txt'])
        )
        template = env.get_template('base.txt')
        render = template.render(user=self.user, listings=self.listings)
        return render

    def send_email(self):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Craigslist Post Matches'
        msg['From'] = Config.sender
        msg['To'] = self.email_address

        text = MIMEText(self.text_message, 'plain')
        msg.attach(text)

        html = MIMEText(self.html_message, 'html')
        msg.attach(html)

        server = smtplib.SMTP(host='smtp.gmail.com', port=587)
        server.starttls()
        server.login(user=Config.sender, password=Config.pwd)
        server.sendmail(Config.sender, self.email_address, msg.as_string())
        server.quit()


class Url:

    def __init__(self, city, category, item_name):
        """
        :param city: string, city / geographical area for craigslist.
        # TODO add in validation for cities (Dict of all NA CL cities?)
        :param category: string, for sale category abbreviation
        # TODO validate categories as well
        """
        assert(city is not None and city.strip() != '')
        assert(category is not None and category.strip() != '')
        assert(item_name is not None and item_name.strip() != '')

        self.city = city.strip()
        self.category = category.strip()
        self.item_name = self.item_name_maker(item_name)

        self.url = f'https://{city}.craigslist.org/search/{category}?' \
                   f'format=rss&searchNearby=1'

    def __repr__(self):
        return f'Url({self.city}, {self.category}, {self.item_name})'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @staticmethod
    def item_name_maker(item_name):
        return '+'.join(item_name.split())


class CarTruck(Url):

    def __init__(self, city, category, item_name, *options):
        """
        :param city: string, city / geographical area for craigslist.
        :param category: string, for sale category abbreviation
        :param item_name: string, item for which user is searching
        :param options: list, search parameters
        """
        Url.__init__(self, city, category, item_name)
        assert item_name is not None

        self.options = options
        self.url = self.url_maker()

    def __repr__(self):
        return f'CarTruck({self.city}, {self.category}, {self.item_name}, *{self.options})'

    def url_maker(self):
        opt = '&'.join([self.url, '&'.join(self.options)])
        if self.item_name.strip() != '':
            return opt + f'&auto_make_model={self.item_name}'
        else:
            return opt
