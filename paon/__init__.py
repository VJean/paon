from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import logging
from logging.handlers import RotatingFileHandler
import paon.tmdbwrap as tmdb


def config_app(flask_app):
    # logging config
    logging.basicConfig(level=logging.DEBUG)

    handler = RotatingFileHandler('paon.log', maxBytes=10000, backupCount=1)
    formatter = logging.Formatter("[%(asctime)s][%(levelname)s]\t[%(name)s]\t %(message)s")
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    flask_app.logger.addHandler(handler)

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
    flask_app.config.from_object('default_config')
    try:
        flask_app.config.from_object('config')
    except ImportError:
        # No custom config found
        flask_app.logger.warn("No custom config found (was searching for config.py)")
        pass
    else:
        # custom config loaded
        tmdb.APIKEY = flask_app.config["APIKEY"]
        flask_app.logger.info("Loaded custom config from config.py")


def create_db(flask_app):
    return SQLAlchemy(flask_app)


def init_db(database):
    from paon.models import Show, Season, Episode
    database.create_all()


# The main Flask app object
app = Flask(__name__)
config_app(app)
db = create_db(app)
init_db(db)

import paon.paon
