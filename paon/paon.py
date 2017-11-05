from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy

from . import tmdbwrap as tmdb


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
    tmdb.APIKEY = app.config["APIKEY"]


# init models database
db = SQLAlchemy(app)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/search/')
def search():
    search = request.args.get('search', None)
    results = []
    if search:
        s = tmdb.Search()
        results = s.tvshow(search)
    return render_template('search.html', shows=results, search=search)
