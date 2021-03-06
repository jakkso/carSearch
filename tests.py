from os import listdir, remove, path
import unittest

import classes

DATABASE = path.join(path.dirname(__file__), 'test.db')
DICT_FILE = path.join(path.dirname(__file__), 'test_dict.p')
URL = 'https://denver.craigslist.org/search/cta?format=rss&bundleDuplicates=1&' \
      'searchNearby=1&min_auto_year=2015&max_auto_miles=30000&auto_make_model=' \
      'GTI&max_price=20000&auto_transmission=1&search_distance=150&postal=80013'


class Base(unittest.TestCase):

    def assert_type_equal(self, obj1, obj2):
        self.assertEqual(type(obj1), type(obj2))


class TestStorage(Base):

    def setUp(self):
        classes.Database.init_database(DATABASE)

    def tearDown(self):
        if 'test.db' in listdir(path.dirname(__file__)):
            remove('test.db')
        if 'test_dict.p' in listdir(path.dirname(__file__)):
            remove('test_dict.p')

    def test_magic_methods(self):
        db = classes.Database(DATABASE)
        self.assertEqual(f'Database("{DATABASE}")', db.__repr__())
        self.assertEqual(f'Database instantiated using {DATABASE} file', db.__str__())

    def test_database_creation(self):
        self.assertIn('test.db', listdir(path.dirname(DATABASE)))
        with classes.Database(DATABASE) as db:
            id, status, url = [item[0] for item in db.cursor.execute('SELECT * FROM posts').description]
        self.assertEqual(id, 'id')
        self.assertEqual(status, 'notification_status')
        self.assertEqual(url, 'url')

    def test_entry_insertion(self):
        id_num = 100
        url = 'www.google.com'
        with classes.Database(DATABASE) as db:
            db.insert_entry(id_num, url)
        with classes.Database(DATABASE) as db:
            c = db.cursor
            c.execute('SELECT * FROM posts')
            res = c.fetchall()[0]
        self.assertEqual(id_num, res[0])
        self.assertEqual(url, res[2])

    def test_load_dict(self):
        feed = classes.Feed(URL, DICT_FILE).load_dict()
        self.assertEqual(len(feed), 0)
        self.assert_type_equal({}, feed)

    def test_save_dict(self):
        test_dict = {1: 1, 2: 2, 3: 3}
        feed = classes.Feed(URL, DICT_FILE)
        feed.feed_dict = test_dict
        feed.save_dict()
        self.assertIn('test_dict.p', listdir(path.dirname(__file__)))
        feed = classes.Feed(URL, DICT_FILE).load_dict()
        self.assertEqual(feed, test_dict)

    def stest_refresh_feed(self):
        feed = classes.Feed(URL, DICT_FILE).refresh_feed()
        self.assertGreater(len(feed), 0)
        feed = classes.Feed(URL, DICT_FILE).refresh_feed()
        self.assertEqual(len(feed), 0)


class TestVehicle(Base):

    def test_url_magic_methods(self):
        denver = classes.Url('Denver', 'cta', 'beetle')
        self.assertEqual(denver.__repr__(), 'Url(Denver, cta, beetle)')
        with classes.Url('Denver', 'cta', 'beetle') as denver:
            self.assertEqual(denver.city, 'Denver')

    def test_url_init(self):
        self.assertEqual('denver', classes.Url('denver ', 'cta', 'beetle').city)
        self.assertEqual('cta', classes.Url('denver', 'cta ', 'beetle').category)
        self.assertEqual('GTI', classes.Url('denver', 'cta', 'GTI ').search_term)
        self.assertEqual('volkswagen+GTI', classes.Url('denver', 'cta',
                                                       'volkswagen GTI').search_term)

    def test_vehicle_magic_methods(self):
        opt = ['max_price=20000', 'auto_transmission=1']
        denver = classes.Vehicle('denver', 'cta', opt, 'GTI')
        self.assertEqual(denver.__repr__(), "Vehicle(denver, cta, ['max"
                                            "_price=20000', 'auto_transmission"
                                            "=1'], GTI)")
        with classes.Vehicle('denver', 'cta', opt, 'GTI') as denver:
            self.assertEqual('denver', denver.city)

    def test_url_maker(self):
        opt = ['max_price=20000', 'auto_transmission=1']
        denver = classes.Vehicle('denver', 'cta', opt, 'GTI')
        self.assertEqual(denver.url, 'https://denver.craigslist.org/search/cta'
                                     '?format=rss&searchNearby=1&max_price=200'
                                     '00&auto_transmission=1&auto_make_model=G'
                                     'TI')
        denver = classes.Vehicle('denver', 'cta', opt, 'GTI ')
        self.assertEqual(denver.url, 'https://denver.craigslist.org/search/cta'
                                     '?format=rss&searchNearby=1&max_price=200'
                                     '00&auto_transmission=1&auto_make_model=G'
                                     'TI')
        denver = classes.Vehicle('denver', 'cta', opt, 'volkswagen GTI')
        self.assertEqual(denver.url, 'https://denver.craigslist.org/search/cta'
                                     '?format=rss&searchNearby=1&max_price=200'
                                     '00&auto_transmission=1&auto_make_model=v'
                                     'olkswagen+GTI')
        denver = classes.Vehicle('denver', 'cta', [], 'GTI')
        self.assertEqual(denver.url, 'https://denver.craigslist.org/search/cta'
                                     '?format=rss&searchNearby=1&auto_make_mod'
                                     'el=GTI')
        denver = classes.Vehicle('denver', 'cta', ['auto_transmission=1'], 'GTI')
        self.assertEqual(denver.url, 'https://denver.craigslist.org/search/cta'
                                     '?format=rss&searchNearby=1&auto_transmis'
                                     'sion=1&auto_make_model=GTI')

    def test_vehicle_options(self):
        static = [
            'posted_today',
            'has_images',
            ('size', 'compact'),
            ('type', 'bus')
        ]

        var = [
            ('min_auto_year', 2015),
            ('postal_code', 80537),
            ('search_distance', 500),
            ('max_price', 20000),
            ('max_miles', 30000)
        ]
        options = classes.VehicleOptions(static, var).options_list
        test_value = ['postToday=1', 'hasPic=1', 'auto_size=1', 'auto_bodytype=1',
                      'min_auto_year=2015', 'postal_code=80537', 'search_distance=500',
                      'max_price=20000', 'max_miles=30000']
        self.assertEqual(options, test_value)

        static.append('nonsense Value')
        var.append(('pfft', 200))
        var.append('pfft')
        options = classes.VehicleOptions(static, var).options_list
        self.assertEqual(test_value, options)

        static = []
        test_value = ['min_auto_year=2015', 'postal_code=80537', 'search_distance=500',
                      'max_price=20000', 'max_miles=30000']
        options = classes.VehicleOptions(static, var).options_list
        self.assertEqual(test_value, options)

        var = []
        test_value = []
        options = classes.VehicleOptions(static, var).options_list
        self.assertEqual(test_value, options)

        static = ['has_images']
        test_value = ['hasPic=1']
        options = classes.VehicleOptions(static, var).options_list
        self.assertEqual(options, test_value)


if __name__ == '__main__':
    unittest.main()
