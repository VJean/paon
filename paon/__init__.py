from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import logging
from logging.handlers import RotatingFileHandler
import paon.tmdbwrap as tmdb


def create_app():
    # The main Flask app object
    app = Flask(__name__)

    # logging config
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

    return app


def create_db(flask_app):
    db = SQLAlchemy(flask_app)
    from paon.models import Show, Season, Episode
    db.create_all()
    return db


app = create_app()
db = create_db(app)


import paon.paon
