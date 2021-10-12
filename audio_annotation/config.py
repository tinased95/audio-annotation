import os
from flask import send_file, make_response
from datetime import datetime
from collections import OrderedDict

"""
Relative or absolute path should be configured here.
Work_PATH is the starting directory. It contains two folders: 
    1. Folder containing the original files
        * Each patient has their own folder.
    2. Folder containing the results of segmentations
        * format is: {patient.name}/{audiofile.id}_{cgsegment.id}.wav
"""

# make sure they all last with /
# LOCAL
#WORK_PATH = os.environ.get('COPD_WORK_PATH', "/Users/tina/PycharmProjects/research/audio-annotator/")
#SEGMENT_FILES_DIRECTORY = 'segments/'
#ORIGINAL_FILES_DIRECTORY = 'wavs/'


# REMOTE
WORK_PATH = os.environ.get('COPD_WORK_PATH', '/Users/tina/PycharmProjects/research/audio_annotation/audio_annotation/data/')
SEGMENT_FILES_DIRECTORY = 'segments/'
ORIGINAL_FILES_DIRECTORY = 'wavs/'

def get_file_path(patient_name, audiofile_id, cgsegment_id):
    return WORK_PATH + SEGMENT_FILES_DIRECTORY + str(patient_name) + '/' + str(audiofile_id) + '_' + str(
        cgsegment_id) + '.wav'


def get_file(patient_name, audiofile_id, cgsegment_id):
    res = make_response(send_file(get_file_path(patient_name, audiofile_id, cgsegment_id)))
    res.headers.add('Cache-Control', 'no-cache, no-store, must-revalidate')
    return res

LIMIT_DATE_TIME = [('copd20', datetime(2016, 11, 26, 19, 58, 00, 0)), ('copd21', datetime(2016, 11, 29, 18, 0, 0))]
FG_LIMIT_DATE_TIME_FLAG = False
