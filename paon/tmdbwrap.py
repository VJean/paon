import requests

LANG = 'fr'
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
