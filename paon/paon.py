from flask import Flask, render_template, request, redirect, flash, url_for
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


class Show(db.Model):
    __tablename__ = 'shows'
    tmdb_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False, unique=True)
    seasons = db.relationship('Season', backref='show')

    def __init__(self, tmdb_id, name):
        self.tmdb_id = tmdb_id
        self.name = name


class Season(db.Model):
    """docstring for Season"""
    __tablename__ = 'seasons'
    tmdb_id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)
    episode_count = db.Column(db.Integer, nullable=False)
    show_id = db.Column(db.Integer, db.ForeignKey('shows.tmdb_id'), nullable=False)

    def __init__(self, tmdb_id, show_id, number, episode_count):
        self.tmdb_id = tmdb_id
        self.show_id = show_id
        self.number = number
        self.episode_count = episode_count


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
    # get show details
    t = tmdb.Tv()
    show = t.by_id(tmdb_id)
    if show is None:
        flash("Une erreur s'est produite.")
        return redirect(url_for('shows'))
    # create show in db
    new_show = Show(show['id'], show['name'])
    for season in show['seasons']:
        new_show.seasons.append(Season(season['id'], tmdb_id, season['season_number'], season['episode_count']))
    db.session.add(new_show)
    db.session.commit()
    # confirm and redirect user
    flash("Ajout effectué")
    return redirect(url_for('shows'))
