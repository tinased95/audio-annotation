# audio-annotation
A web interface for annotating audio data.

### Description
audio-annotation is a web application that allows users to annotatate audio files. It is developed using Python (Flask), Javascript, HTML5/CSS3, and Postgresql. 
It is extended from [audio-annotator](https://github.com/CrowdCurio/audio-annotator).

### Benefits:
1. Admin page to view and manage tables. 

### Data format
WORK_PATH = is the starting directory.
ORIGINAL_FILES_DIRECTORY= is the audio file directory (in this directory the folders should be named based on the participant and their audio recordings are located inside them)
SEGMENT_FILES_DIRECTORY= After removing silence intervals and performing segmentation, the audio segments will be automatically created here.

### Database setup
1. Download [postgresql](https://www.postgresql.org/download/).
2. createdb databasename

### environmental variables:
* export EMAIL_SENDER= The email used for sending errors
* export EMAIL_PASSWORD= The email password
* export EMAIL_RECEIVER= The email used for receiving errors
* export  DB_NAME= Database name
* export  DB_USER= Database username
* export  DB_PASSWORD= Database password
* export FIRST_RUN=True # for the first time running the server, otherwise False

### Run app
gunicorn --bind 0.0.0.0:5000 --workers=1 --timeout=0 --access-logfile access.log  run:app
