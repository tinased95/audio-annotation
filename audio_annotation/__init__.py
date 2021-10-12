from flask import Flask, config
from flask_jsglue import JSGlue
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail
import os

app = Flask(__name__)

jsglue = JSGlue()
jsglue.init_app(app)

app.config.update(dict(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=465,
    MAIL_USE_SSL=True,
    MAIL_USE_TLS=False,
    MAIL_USERNAME=os.environ['EMAIL_SENDER'],
    MAIL_PASSWORD=os.environ['EMAIL_PASSWORD'],
    MAIL_DEFAULT_SENDER=os.environ['EMAIL_SENDER']
  
))


mail = Mail()
mail.init_app(app)
app.config['SECRET_KEY'] = '\nis\xe2W\xba\x9aw\xa1LD\xce\x16\xe1\xe7\xe5\xc2K*\x0eu\xee\xd3\xe8'
# where the database is located /// :relative path, //// :absolute path
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
# backupdb
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://' + os.environ['DB_USER'] + ':' + os.environ['DB_PASSWORD'] + '@localhost/' + os.environ['DB_NAME'] 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.url_map.strict_slashes = False

# initialize the database
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

from workallocator import WorkAllocator
from audio_annotation import dataLoader
import reset

## if os.environ['FIRST_RUN']:
if os.getenv('FIRST_RUN', 'False').lower() != 'false':
    db.create_all()
    dataLoader.load_data()
    reset.reset_database()
    
    print("Data loaded")

cgworkallocator = WorkAllocator(db, 'cg')
fgworkallocator = WorkAllocator(db, 'fg')

FROM_EMAIL = 'from@mail.com'
TO_EMAIL = 'to@mail.com'

from audio_annotation import routes
from audio_annotation import coarseGrainedAnnotation
from audio_annotation import fineGrainedAnnotation
# from audio_annotation import about
# from audio_annotation import createUser
from audio_annotation import functions
from audio_annotation import admin_pages
