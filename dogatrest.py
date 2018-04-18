import falcon
import logging
import datetime
import requests
import json
from apscheduler.schedulers.background import BackgroundScheduler

logging.basicConfig(level=logging.INFO)


class StorageEngine:
    """
    Simple key value store.
    """

    def __init__(self):
        self.store = dict()

    def __getitem__(self, key):
        key = tuple(key)
        try:
            value = self.store[key]
        except KeyError:
            raise StorageError(f'No entry found for {key}.')
        return value

    def __setitem__(self, key, value):
        key = tuple(key)
        self.store[key] = value

    def load_file(self, filename, prefix=None):
        with open(filename) as f:
            items = json.load(f)
        for id, item in items.items():
            if prefix is not None:
                self.store[prefix, id] = item
            else:
                self.store[id] = item
        logging.info(f'Loaded {len(items)} items to db.')



class StorageError(Exception):
    def __init__(self, message):
        self.message = message

    @staticmethod
    def handle(ex, req, resp, params):
        description = (f'Sorry, could not write or read your thing to or from the '
                       f'database: {ex.message}.')
        raise falcon.HTTPError(falcon.HTTP_725,
                               'Database Error',
                               description)


class RequireJSON:

    def process_request(self, req, resp):
        if not req.client_accepts_json:
            raise falcon.HTTPNotAcceptable(
                'This API only supports responses encoded as JSON.',
                href='http://docs.examples.com/api/json')

        if req.method in ('POST', 'PUT'):
            if 'application/json' not in req.content_type:
                raise falcon.HTTPUnsupportedMediaType(
                    'This API only supports requests encoded as JSON.',
                    href='http://docs.examples.com/api/json')


def max_body(limit):

    def hook(req, resp, resource, params):
        length = req.content_length
        if length is not None and length > limit:
            msg = ('The size of the request is too large. The body must not '
                   'exceed ' + str(limit) + ' bytes in length.')

            raise falcon.HTTPRequestEntityTooLarge(
                'Request body is too large', msg)

    return hook


class DogResource:

    def __init__(self, db):
        self.db = db

    def on_get(self, req, resp, dog_id):
        # Upon get, we return the data
        resp.media = self.db['dog', dog_id]
        resp.status = falcon.HTTP_200

    @falcon.before(max_body(64 * 1024))
    def on_post(self, req, resp, dog_id):
        # Upon post we reset the last_time
        data = req.context or dict()
        now = datetime.datetime.utcnow()

        dog = self.db['dog', dog_id]
        dog['last_time'] = now.timestamp()
        dog['last_time_str'] = now.isoformat()
        dog['last_data'] = data
        self.db['dog', dog_id] = dog

        resp.status = falcon.HTTP_200
        resp.media = self.db['dog', dog_id]


def check_dogs():
    dogs = {id: value for (_, id), value in db.store.items()}
    overdue = dict()
    now = datetime.datetime.utcnow().timestamp()
    for id, dog in dogs.items():
        if 'last_time' in dog:
            delta = (now - dog['last_time']) / 60
            if delta > dog['interval'] and dog.get('alive', True):
                dog['bark_status'] = bark_dead(dog)
                dog['alive'] = False
            elif delta < dog['interval'] and not dog.get('alive', False):
                dog['bark_status'] = bark_alive(dog)
                dog['alive'] = True
        if not dog.get('alive', True):
            overdue[id] = dog

    logging.info(f'{len(overdue)} dogs are dead.')
    return overdue


def bark_dead(dog):
    default_template = {'message': 'I am probably dead. Could anyone check?', 'user': '{name}'}
    data = dict()
    for key, value in dog.get('template_dead', default_template).items():
        data[key] = value.format(**dog)
    r = requests.post(dog['hook'], json=data)
    logging.info(f"Hooked {dog['name']}: Dead.")
    return r.status_code


def bark_alive(dog):
    default_template = {'message': 'Back to life! Thanks.', 'user': '{name}'}
    data = dict()
    for key, value in dog.get('template_alive', default_template).items():
        data[key] = value.format(**dog)
    r = requests.post(dog['hook'], json=data)
    logging.info(f"Hooked {dog['name']}: Alive.")
    return r.status_code


db = StorageEngine()
db.load_file('data/dogs.json', 'dog')

app = falcon.API(middleware=[
    RequireJSON(),
])

dogs = DogResource(db)
app.add_route('/dog/{dog_id}/', dogs)
app.add_error_handler(StorageError, StorageError.handle)

scheduler = BackgroundScheduler(timezone='UTC')
scheduler.add_job(check_dogs, 'interval', seconds=60)
scheduler.start()
