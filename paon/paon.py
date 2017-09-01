from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import requests


app = Flask(__name__)

# Loading default config
app.config.from_object('default_config')
try:
    app.config.from_object('config')
except ImportError:
    # No custom config found
    pass
else:
    # custom config loaded
    pass

# init models database
db = SQLAlchemy(app)

APIKEY = '353fa1f8f5c71a9822703a5a5d5b8faf'
LANG = 'fr'
API_URL = 'https://api.themoviedb.org/3/'
TV_URL = 'https://api.themoviedb.org/3/tv/{id}'


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/search/')
def search():
    search = request.args.get('search', None)
    results = []
    if search:
        url = API_URL + 'search/tv'
        payload = {
            "language": LANG,
            "api_key": APIKEY,
            "query": search
        }
        req = requests.get(url, params=payload)
        if req.status_code == 200:
            results = req.json()['results']
    return render_template('search.html', shows=results, search=search)
