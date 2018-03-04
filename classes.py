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
        self.item_name = '+'.join(item_name.split())

        self.url = f'https://{city}.craigslist.org/search/{category}?' \
                   f'format=rss&searchNearby=1'

    def __repr__(self):
        return f'Url({self.city}, {self.category}, {self.item_name})'

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


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

        self.options = self.options_maker(options)
        self.url = self.url_maker()

    def __repr__(self):
        return f'CarTruck({self.city}, {self.category}, {self.item_name}, *{self.options})'

    @staticmethod
    def options_maker(options):
        if len(options) > 1:
            return options
        elif len(options) == 1 and options[0] != [] and options[0][0].strip() != '':
            return options[0]
        else:
            return []

    def url_maker(self):
        if len(self.options) > 1:
            opt = '&'.join([self.url, '&'.join(self.options)])
        elif len(self.options) == 1 and self.options[0] != []:
            opt = f'{self.url}&{self.options[0]}'
        else:
            opt = self.url
        if self.item_name != '':
            return opt + f'&auto_make_model={self.item_name}'
        else:
            return opt


class CTOptions:
    flat_static = {
        'crypto': 'crypto_currency_ok=1',
        'posted_today': 'postToday=1',
        'bundled_duplicates': 'bundleDuplicates=1',
        'has_images': 'hasPic=1',
        'titles_only': 'srchType=T',
    }
    nested_static = {
        'condition': {
            'new': 'condition=10',
            'like new': 'condition=20',
            'excellent': 'condition=30',
            'good': 'condition=40',
            'fair': 'condition=50',
            'salvage': 'condition=60'},
        'cylinders': {
            '3': 'auto_cylinders=1',
            '4': 'auto_cylinders=2',
            '5': 'auto_cylinders=3',
            '6': 'auto_cylinders=4',
            '8': 'auto_cylinders=5',
            '10': 'auto_cylinders=6',
            '12': 'auto_cylinders=7',
            'other': 'auto_cylinders=8'},
        'drive': {
            'fwd': 'auto_drivetrain=1',
            'rwd': 'auto_drivetrain=2',
            '4wd': 'auto_drivetrain=3'},
        'fuel': {
            'gas': 'auto_fuel_type=1',
            'diesel': 'auto_fuel_type=2',
            'hybrid': 'auto_fuel_type=3',
            'electric': 'auto_fuel_type=4',
            'other': 'auto_fuel_type=6'},
        'color': {
            'black': 'auto_paint=1',
            'blue': 'auto_paint=2',
            'brown': 'auto_paint=20',
            'green': 'auto_paint=3',
            'grey': 'auto_paint=4',
            'orange': 'auto_paint=5',
            'purple': 'auto_paint=6',
            'red': 'auto_paint=7',
            'silver': 'auto_paint=8',
            'white': 'auto_paint=9',
            'yellow': 'auto_paint=10',
            'custom': 'auto_paint=11'},
        'size': {
            'compact': 'auto_size=1',
            'full-size': 'auto_size=2',
            'mid-size': 'auto_size=3',
            'sub-compact': 'auto_size=4'},
        'title-status': {
            'clean': 'auto_title_status=1',
            'salvage': 'auto_title_status=2',
            'rebuilt': 'auto_title_status=3',
            'parts-only': 'auto_title_status=4',
            'lien': 'auto_title_status=5',
            'missing': 'auto_title_status=6'},
        'transmission': {
            'manual': 'auto_transmission=1',
            'automatic': 'auto_transmission=2',
            'other': 'auto_transmission=3'},
        'type': {
            'bus': 'auto_bodytype=1',
            'convertible': 'auto_bodytype=2',
            'coupe': 'auto_bodytype=3',
            'hatchback': 'auto_bodytype=4',
            'mini-van': 'auto_bodytype=5',
            'offroad': 'auto_bodytype=6',
            'pickup': 'auto_bodytype=7',
            'sedan': 'auto_bodytype=8',
            'truck': 'auto_bodytype=9',
            'SUV': 'auto_bodytype=10',
            'wagon': 'auto_bodytype=11',
            'van': 'auto_bodytype=12',
            'other': 'auto_bodytype=13'},

    }
    var_opt = {
        'search_distance': 'search_distance',
        'postal_code': 'postal',
        'min_price': 'min_price',
        'max_price': 'max_price',
        'min_auto_year': 'min_auto_year',
        'max_auto_year': 'max_auto_year',
        'min_miles': 'min_auto_miles',
        'max_miles': 'max_auto_miles'
    }

    def __init__(self, static, var):
        """
        :param static: list of strings and 2-tuples, options whose value is static
        :param var: list of 2-tuples, each list element is made of option
                    and the variable option amount
        """
        self.static = static
        self.var = var
        self.options = self.list_builder()

    @staticmethod
    def opt_builder(option, amount):
        return f'{option}={amount}'

    @property
    def options_list(self):
        return self.options

    def list_builder(self):
        """
        :return: list of search options
        """
        options = []
        for option in self.static:
            if option in self.flat_static:
                options.append(self.flat_static[option])

            else:
                try:
                    opt, value = option
                    if opt in self.nested_static:
                        options.append(self.nested_static[opt][value])
                except ValueError as e:
                    print(f'Error: {e}.  \nPassing')

        for option in self.var:
            try:
                opt, amount = option
                if opt in self.var_opt:
                    options.append(self.opt_builder(opt, amount))
            except ValueError as e:
                print(f'Error: {e}. \nPassing')
        return options
