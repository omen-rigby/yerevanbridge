import os
import psycopg2
import urllib.parse as up


def connect():
    db_path = os.environ.get('DB_URL')
    url = up.urlparse(db_path)
    return psycopg2.connect(database=url.path[1:],
                            user=url.username,
                            password=url.password,
                            host=url.hostname,
                            port=url.port
                            )


class Dict2Class(object):

    def __init__(self, my_dict):
        self.dict = my_dict
        for key in my_dict:
            setattr(self, key, my_dict[key])

    def __str__(self):
        return '{' + \
               ", ".join(f"{k}: " + ("list" if type(v) == list else v.__str__()) for k, v in self.dict.items()) + '}'


def nbsp_names(text):
    text = text.replace(' & ', '!').replace(' ', '&nbsp;').replace('!', ' & ')
    return text


def hcp(hand):
    h = hand.lower()
    return 4 * h.count('a') + 3 * h.count('k') + 2 * h.count('q') + h.count('j')
