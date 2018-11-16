from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# init models database
db = SQLAlchemy(app)

import paon.paon
#from .paon import update
