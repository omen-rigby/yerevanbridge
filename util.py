import os
import psycopg2
import math
import urllib.parse as up
from flask import render_template


def static_page(key, locale):
    conn = None
    try:
        conn = connect()
        cursor = conn.cursor()
        cursor.execute(f"""select value from strings where "key"='{key}_{locale}'""")
        content = cursor.fetchone()[0]
        return render_template(f'{key}.html', content=content)
    except Exception:
        return render_template(f'{key}.html')
    finally:
        if conn:
            conn.close()


def localize_names(cursor, data, locale, index=None):
    return_first = False
    if locale != 'ru':
        cursor.execute(f'''select full_name, full_name_{locale} from players''')
        names = cursor.fetchall()
        if type(data) == str:
            data = [data]
            return_first = True
        else:
            data = list(data)
        for i, name in enumerate(data):
            if name is None:
                continue
            if index is None:
                data[i] = ' & '.join(map(lambda x: [n[1] for n in names if x.strip() == n[0].strip()][0],
                                         name.split(' & ')))
            else:
                try:
                    new_value = list(map(lambda x: [n[1] for n in names if x.strip() == n[0].strip()][0],
                                         name[index].split(' & ')))

                    data[i] = list(data[i])
                    data[i][index] = ' & '.join(new_value)
                except IndexError:
                    pass
    return data[0] if return_first else data


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


def vp(score, boards):
    """https://www.bridgebase.com/forums/topic/55389-wbf-vp-scale-changes/page__p__667202#entry667202"""
    phi = (5 ** .5 - 1) / 2
    b = 15 * (boards ** .5)
    margin = abs(score)
    vp_winner = 10 + 10 * ((1 - phi ** (3 * margin / b)) / (1 - phi ** 3))
    vp_winner = min(round(math.floor(vp_winner * 1000) / 1000, 2), 20)
    vp_loser = 20 - vp_winner
    return vp_winner if score > 0 else vp_loser
