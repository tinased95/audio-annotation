# audio-annotation
A web interface for annotating audio data.

### Description
audio-annotation is a web application that allows users to annotatate audio files. It is developed using Python (Flask), Javascript, HTML5/CSS3, and Postgresql. 
It is extended from [audio-annotator](https://github.com/CrowdCurio/audio-annotator).

### Benefits:
1. Admin page to view and manage tables. 


#### environmental variables:
* export EMAIL_SENDER= The email used for sending errors
* export EMAIL_PASSWORD= The email password
* export EMAIL_RECEIVER= The email used for receiving errors
* export  DB_NAME= Database name
* export  DB_USER= Database username
* export  DB_PASSWORD= Database password
* export FIRST_RUN=True # for the first time running the server, otherwise False

