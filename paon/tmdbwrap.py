import requests

LANG = 'en'
APIKEY = None
APIURL = 'https://api.themoviedb.org/3/'


class Search(object):
    """docstring for Search"""

    def __init__(self):
        super(Search, self).__init__()
        self.BASEPATH = APIURL + 'search/'

    def tvshow(self, query):
        PATH = self.BASEPATH + 'tv/'
        payload = {
            "language": LANG,
            "api_key": APIKEY,
            "query": query
        }
        req = requests.get(PATH, params=payload)
        if req.status_code == 200:
            return req.json()['results']
        else:
            return []


class Tv(object):
    """docstring for Tv"""
    def __init__(self):
        super(Tv, self).__init__()
        self.BASEPATH = APIURL + 'tv/'

    def by_id(self, id):
        PATH = self.BASEPATH + '{0}'.format(id)
        payload = {
            "language": LANG,
            "api_key": APIKEY
        }
        req = requests.get(PATH, params=payload)
        if req.status_code == 200:
            return req.json()
        else:
            return None
