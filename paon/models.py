import datetime

from paon import db


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