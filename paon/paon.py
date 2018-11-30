from flask import abort, render_template, request, redirect, flash, url_for
import datetime
import logging
from logging.handlers import RotatingFileHandler

from . import tmdbwrap as tmdb
from . import app, db
import paon.utils as utils

logging.basicConfig(level=logging.DEBUG)

handler = RotatingFileHandler('paon.log', maxBytes=10000, backupCount=1)
formatter = logging.Formatter("[%(asctime)s][%(levelname)s]\t[%(name)s]\t %(message)s")
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
app.logger.addHandler(handler)

wlog = logging.getLogger('werkzeug')
wlog.setLevel(logging.DEBUG)
wlog.addHandler(handler)

apilog = logging.getLogger('paon.tmdbwrap')
apilog.setLevel(logging.INFO)
apilog.addHandler(handler)
urlliblog = logging.getLogger('urllib3')
urlliblog.setLevel(logging.WARN)
urlliblog.addHandler(handler)

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


class Show(db.Model):
    __tablename__ = 'shows'
    tmdb_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False, unique=True)
    season_count = db.Column(db.Integer, nullable=False)
    seasons = db.relationship('Season', backref='show', lazy='dynamic', cascade="all, delete-orphan")
    episodes = db.relationship('Episode', backref='show', lazy='dynamic', cascade="all, delete-orphan")

    def __init__(self, tmdb_id, name, season_count):
        self.tmdb_id = tmdb_id
        self.name = name
        self.season_count = season_count

    def get_season(self, season_number):
        return self.seasons.filter(Season.number == season_number).first()

    def not_seen(self):
        not_seen = []
        for s in self.seasons:
            not_seen.extend(s.not_seen())
        return not_seen

    def seen(self):
        seen = []
        for s in self.seasons:
            seen.extend(s.seen())
        return seen

    def last_aired(self):
        e = self.episodes.filter(
            Episode.air_date <= datetime.date.today()
        ).order_by(Episode.air_date.desc(), Episode.number.desc()).first()
        return e

    def last_seen(self):
        seen = self.seen()
        if len(seen) == 0:
            return None
        ordered = sorted(seen, key=lambda e: (e.air_date, e.number), reverse=True)
        return ordered[0]

    @property
    def progression(self):
        not_seen_nb = len(self.not_seen())
        seen_nb = len(self.seen())
        if not_seen_nb == 0:
            return 100
        return (seen_nb / (seen_nb + not_seen_nb)) * 100

    def __lt__(self, other):
        return self.name < other.name


class Season(db.Model):
    __tablename__ = 'seasons'
    tmdb_id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)
    air_date = db.Column(db.Date, nullable=False)
    episode_count = db.Column(db.Integer, nullable=False)
    show_id = db.Column(db.Integer, db.ForeignKey('shows.tmdb_id'), nullable=False)
    episodes = db.relationship('Episode', backref='season', lazy='dynamic', cascade="all, delete-orphan")

    def __init__(self, tmdb_id, show_id, number, episode_count, air_date):
        self.tmdb_id = tmdb_id
        self.show_id = show_id
        self.number = number
        self.episode_count = episode_count
        self.air_date = air_date

    def not_seen(self):
        return [e for e in self.episodes if (not e.watched) and e.has_aired()]

    def seen(self):
        return [e for e in self.episodes if e.watched]

    def progression(self):
        not_seen_nb = len(self.not_seen())
        if not_seen_nb == 0:
            return 100
        return len(self.seen()) / not_seen_nb * 100

    def has_aired(self):
        return self.air_date <= datetime.date.today()


class Episode(db.Model):
    __tablename__ = 'episodes'
    tmdb_id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.Integer, nullable=False)
    air_date = db.Column(db.Date, nullable=False)
    watched = db.Column(db.Boolean, default=False)
    watch_date = db.Column(db.Date)
    season_id = db.Column(db.Integer, db.ForeignKey('seasons.tmdb_id'), nullable=False)
    show_id = db.Column(db.Integer, db.ForeignKey('shows.tmdb_id'), nullable=False)

    def __init__(self, tmdb_id, show_id, season_id, number, air_date):
        self.tmdb_id = tmdb_id
        self.show_id = show_id
        self.season_id = season_id
        self.number = number
        self.air_date = air_date

    def __repr__(self):
        return f"S{self.season.number:02d}E{self.number:02d}"

    def has_aired(self):
        return self.air_date <= datetime.date.today()


db.create_all()


@app.route('/search/')
def search():
    search_str = request.args.get('search', None)
    results = []
    if search_str:
        s = tmdb.Search()
        results = s.tvshow(search_str)
    return render_template('search.html', shows=results, search=search_str)


@app.route('/', methods=['GET'])
def get_shows():
    # return all followed shows
    shows = Show.query.all()
    # return episodes that air during the upcoming week
    today = datetime.datetime.today()
    upcoming = Episode.query.filter(Episode.air_date >= today, Episode.air_date <= today + datetime.timedelta(7)).all()
    return render_template('shows.html', shows=shows, upcoming=upcoming)


@app.route('/add', methods=['GET'])
def add_show():
    # get id and name from request
    tmdb_id = request.args.get('id', None)
    if tmdb_id is None:
        return redirect(url_for('shows'))
    elif Show.query.get(tmdb_id) is not None:
        return "Cette série est déjà suivie"
    app.logger.info(f"Getting show {tmdb_id} from tmdb")
    # get show details
    t = tmdb.Tv()
    ts = tmdb.TvSeasons()
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
            utils.tmdb_date_to_date(season['air_date']))
        # get season object
        season_obj = ts.by_id(show['id'], season['season_number'])
        # fetch episodes
        for ep in season_obj['episodes']:
            new_ep = Episode(
                ep['id'],
                tmdb_id,
                season_obj['id'],
                ep['episode_number'],
                utils.tmdb_date_to_date(ep['air_date']))
            new_season.episodes.append(new_ep)
        new_show.seasons.append(new_season)
    db.session.add(new_show)
    db.session.commit()
    app.logger.info(f"Added show {tmdb_id} ({new_show.name}) to database")
    # confirm and redirect user
    flash("Ajout effectué")
    return redirect(url_for('shows'))


@app.route('/shows/<int:show_id>')
def show(show_id):
    show = Show.query.get(show_id)
    if show is None:
        abort(404)
    return render_template('show.html', show=show)


@app.route('/shows/<int:show_id>/update')
def update_show(show_id):
    # get id and name from request
    show = Show.query.get(show_id)
    ep_id = request.args.get('ep', None)
    if ep_id is None:
        abort(400)
    episode = Episode.query.get(ep_id)
    if show is None or episode is None:
        abort(404)

    # check that episode is part of the show
    if episode.season.show_id != show_id:
        abort(400)

    # mark all episodes from beginning as watched
    mark_as_watched = []
    season_nb = episode.season.number
    if season_nb > 1:
        for s in Season.query.filter(Season.show_id == show_id, Season.number < season_nb).all():
            mark_as_watched.extend(s.episodes)
    for ep_current_season in [e for e in episode.season.episodes if e.number <= episode.number]:
        ep_current_season.watched = True
    for e in mark_as_watched:
        e.watched = True

    db.session.commit()
    return redirect(url_for('show', show_id=show_id))


def remove_show(show_id):
    """
    Delete a show from the database.
    The deletion process will also delete related seasons and episodes.
    """
    try:
        Show.query.get(show_id).delete()
    finally:
        return


def update():
    myshows = Show.query.all()
    t = tmdb.Tv()
    ts = tmdb.TvSeasons()
    for myshow in myshows:
        show = t.by_id(myshow.tmdb_id)
        last_aired_date = utils.tmdb_date_to_date(show['last_air_date'])
        last_local_episode = Episode.query.filter(
            Episode.show_id == myshow.tmdb_id
        ).order_by(Episode.air_date.desc()).first()
        app.logger.info(f"{myshow.name}: local: {last_local_episode.air_date}, most recent: {last_aired_date}")
        if last_aired_date > last_local_episode.air_date:
            app.logger.info(f"{myshow.name} needs an update")
            # get last season
            mylastseason = myshow.get_season(myshow.season_count)
            lastseason = ts.by_id(myshow.tmdb_id, myshow.season_count)
            missing_count = len(lastseason['episodes']) - mylastseason.episode_count
            for i in range(mylastseason.episode_count, mylastseason.episode_count + missing_count):
                ep = lastseason['episodes'][i]
                new_ep = Episode(
                    ep['id'],
                    myshow.tmdb_id,
                    lastseason['id'],
                    ep['episode_number'],
                    utils.tmdb_date_to_date(ep['air_date']))
                mylastseason.episodes.append(new_ep)

            mylastseason.episode_count = len(mylastseason.episodes)

            # are we also missing seasons ?
            seasons_diff = show['number_of_seasons'] - myshow.season_count
            if seasons_diff > 0:
                for new_s in show['seasons']:
                    if new_s['season_number'] <= mylastseason.number:
                        continue
                    new_season = Season(
                        new_s['id'],
                        myshow.tmdb_id,
                        new_s['season_number'],
                        new_s['episode_count'],
                        utils.tmdb_date_to_date(new_s['air_date']))
                    # get season object
                    season_obj = ts.by_id(myshow.tmdb_id, new_s['season_number'])
                    # fetch episodes
                    for ep in season_obj['episodes']:
                        new_ep = Episode(
                            ep['id'],
                            myshow.tmdb_id,
                            season_obj['id'],
                            ep['episode_number'],
                            utils.tmdb_date_to_date(ep['air_date']))
                        new_season.episodes.append(new_ep)
                    myshow.seasons.append(new_season)
                    myshow.season_count = len(myshow.seasons)

            db.session.commit()
            app.logger.info(f"{myshow.name} is up to date")
