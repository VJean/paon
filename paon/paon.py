from flask import Flask, render_template, request, redirect, flash, url_for
from flask_sqlalchemy import SQLAlchemy
import datetime
import logging
from logging.handlers import RotatingFileHandler

from . import tmdbwrap as tmdb

app = Flask(__name__)
handler = RotatingFileHandler('paon.log', maxBytes=10000, backupCount=1)
formatter = logging.Formatter("[%(asctime)s][%(levelname)s]\t[%(name)s]\t %(message)s")
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
app.logger.addHandler(handler)

wlog = logging.getLogger('werkzeug')
wlog.setLevel(logging.DEBUG)
wlog.addHandler(handler)

apilog = logging.getLogger('paon.tmdbwrap')
apilog.setLevel(logging.INFO)
apilog.addHandler(handler)


# Loading default config
app.config.from_object('default_config')
try:
    app.config.from_object('config')
except ImportError:
    # No custom config found
    app.logger.warn("No custom config found (was searching for config.py)")
    pass
else:
    # custom config loaded
    tmdb.APIKEY = app.config["APIKEY"]
    app.logger.info("Loaded custom config from config.py")


# init models database
db = SQLAlchemy(app)


class Show(db.Model):
    __tablename__ = 'shows'
    tmdb_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False, unique=True)
    season_count = db.Column(db.Integer, nullable=False)
    seasons = db.relationship('Season', backref='show')

    def __init__(self, tmdb_id, name, season_count):
        self.tmdb_id = tmdb_id
        self.name = name
        self.season_count = season_count


class Season(db.Model):
    __tablename__ = 'seasons'
    tmdb_id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)
    air_date = db.Column(db.Date, nullable=False)
    episode_count = db.Column(db.Integer, nullable=False)
    show_id = db.Column(db.Integer, db.ForeignKey('shows.tmdb_id'), nullable=False)
    episodes = db.relationship('Episode', backref='season')

    def __init__(self, tmdb_id, show_id, number, episode_count, air_date):
        self.tmdb_id = tmdb_id
        self.show_id = show_id
        self.number = number
        self.episode_count = episode_count
        self.air_date = air_date


class Episode(db.Model):
    __tablename__ = 'episodes'
    tmdb_id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)
    air_date = db.Column(db.Date, nullable=False)
    watch_date = db.Column(db.Date)
    season_id = db.Column(db.Integer, db.ForeignKey('seasons.tmdb_id'), nullable=False)

    def __init__(self, tmdb_id, season_id, number, air_date):
        self.tmdb_id = tmdb_id
        self.season_id = season_id
        self.number = number
        self.air_date = air_date


db.create_all()


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


@app.route('/shows/', methods=['GET'])
def shows():
    shows = Show.query.all()
    return render_template('shows.html', shows=shows)


@app.route('/shows/add', methods=['GET'])
def add_show():
    # get id and name from request
    tmdb_id = request.args.get('id', None)
    if id is None:
        return redirect(url_for('shows'))
    app.logger.info(f"Getting show {tmdb_id} from tmdb")
    # get show details
    t = tmdb.Tv()
    show = t.by_id(tmdb_id)
    if show is None:
        app.logger.warn(f"Got None when searching tmdb for {tmdb_id}")
        flash("Une erreur s'est produite.")
        return redirect(url_for('shows'))
    # create show in db
    new_show = Show(
        show['id'],
        show['name'],
        show['number_of_seasons'])
    # fetch seasons
    for season in show['seasons']:
        # avoid season 0 that is usually Specials
        if season['season_number'] == 0:
            continue
        new_season = Season(
            season['id'],
            tmdb_id,
            season['season_number'],
            season['episode_count'],
            tmdb_date_to_date(season['air_date']))
        # fetch episodes
        for ep_nb in range(season['episode_count']):
            continue
        new_show.seasons.append(new_season)
    db.session.add(new_show)
    db.session.commit()
    app.logger.info(f"Added show {tmdb_id} ({new_show.name}) to database")
    # confirm and redirect user
    flash("Ajout effectué")
    return redirect(url_for('shows'))


def tmdb_date_to_date(str):
    d = datetime.datetime.strptime(str, '%Y-%m-%d')
    return d.date()
