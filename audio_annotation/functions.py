import os
import sys

from flask import session
from sqlalchemy import func
from flask_mail import Message
from audio_annotation.models import Telemetry, CGLogTask, FGLogTask, FGLogBatch, CGTask,\
    FGTask, User, Patient
from audio_annotation import db, mail
import pandas as pd
from audio_annotation.config import WORK_PATH, SEGMENT_FILES_DIRECTORY
from flask import send_file, make_response
import json
from collections import OrderedDict
from datetime import datetime
from server_statics import cg_test_initial_true_labels, fg_test_initial_true_labels


def get_latest_labels(labeltable, tasktable, annotator_id, batch_number):
    subquery = db.session.query(
        labeltable, tasktable.cgsegment_id,
        func.rank().over(
            order_by=labeltable.submit_time.desc(),
            partition_by=labeltable.task_id
        ).label('rnk')
    ).outerjoin(tasktable).filter((labeltable.annotator_id == annotator_id) & (
                labeltable.batch_number == batch_number)).subquery()  # & (CGLabel.batch_number.in_([1,2]))
    return pd.read_sql(db.session.query(subquery).filter(subquery.c.rnk == 1).statement, db.session.bind)


def getOverlap(a, b):
    intersection = max(0, min(a[1], b[1]) - max(a[0], b[0]))
    return intersection / ((a[1] - a[0]) + (b[1] - b[0]) - intersection)


def calc_jaccard_index_initial(annotation_type, latestlabels):
    result = []
    percentage = 0
    count = 0
    if len(latestlabels) == 0:
        return [], 0
    if annotation_type == 'cg':
        for label in latestlabels.itertuples():  # each task
            count += 1
            if cg_test_initial_true_labels[label.cgsegment_id] == label.label:
                result.append((label.cgsegment_id, 1))
                percentage += 1
            else:
                result.append((label.cgsegment_id, 0))
        # percentage = percentage / len(latestlabels)
    else:  # if fg
        grouped = latestlabels.groupby('cgsegment_id')
        for cgsegment_id, group in grouped:  # for each segment
            segment_jaccard = 0
            for true_label in fg_test_initial_true_labels[cgsegment_id]:  # for each true label for this segment
                for label in group.itertuples():  # for each label in this segment
                    segment_jaccard += getOverlap(true_label, [label.start, label.end])
            result.append((cgsegment_id, segment_jaccard / len(fg_test_initial_true_labels[cgsegment_id])))
            count += 1
            percentage += segment_jaccard

    percentage = percentage / count
    return result, percentage

def select_task_in_batch(batchtable, batch_id, annotator_id, num_in_batch, batch_number):
    return db.session.query(batchtable).filter(batchtable.id == batch_id).filter(
        batchtable.annotator_id == annotator_id).filter(
        batchtable.num_in_batch == num_in_batch).filter(batchtable.batch_number == batch_number).one()

def latest_num_in_batch(batchtable, annotator_id, batch_number):
    return db.session.query(batchtable.num_in_batch).filter(batchtable.annotator_id == annotator_id).filter(
        batchtable.batch_number == batch_number).filter(batchtable.is_done == True).order_by(
        batchtable.num_in_batch.desc()).first()

def get_latest_flag(flagtable, task_id, annotator_id, batch_number):
    flag = db.session.query(flagtable).filter((flagtable.task_id == task_id) & (flagtable.annotator_id == annotator_id) & (flagtable.batch_number == batch_number))\
        .order_by(flagtable.submit_time.desc()).first()
    return flag


def insert_flag(flagtable, task_id, description, annotator_id, batch_number, submit_time):
    flag = flagtable(task_id=task_id, description=description, annotator_id=annotator_id, batch_number=batch_number, submit_time=submit_time)
    db.session.add(flag)

def update_sessions(action, annotation_type):
    if annotation_type == 'cg':
        if action == 'replay-btn':
            session[annotation_type+'-numReplay'] += 1
    elif annotation_type == 'fg':
        if action == 'click-play' or action == 'spacebar-play':
            session[annotation_type+'-numPlay'] += 1
        elif action == 'click-pause' or action == 'spacebar-pause':
            session[annotation_type+'-numPause'] += 1
        elif action == 'delete':
            session[annotation_type+'-numDelete'] += 1
        elif action == 'start-to-create':
            session[annotation_type+'-numCreate'] += 1
        elif action == 'region-moved-drag':
            session[annotation_type+'-numMove'] += 1
        elif action == 'region-moved-start' or action == 'region-moved-end':
            session[annotation_type+'-numResize'] += 1
        elif action == 'play-region':
            session[annotation_type+'-numPlayRegion'] += 1

def get_file_path(patient_name, audiofile_id, cgsegment_id):
    return WORK_PATH + SEGMENT_FILES_DIRECTORY + str(patient_name) + '/' + str(audiofile_id) + '_' + str(
        cgsegment_id) + '.wav'


def get_file(patient_name, audiofile_id, cgsegment_id):
    print(get_file_path(patient_name, audiofile_id, cgsegment_id))
    res = make_response(send_file(get_file_path(patient_name, audiofile_id, cgsegment_id)))
    res.headers.add('Cache-Control', 'no-cache, no-store, must-revalidate')
    return res

# logs
def save_telemetry(annotator_id, ts, action, annotation_type=None, task_id=None, batch_number=None, extra_info=None):
    telemetry = Telemetry(annotator_id=annotator_id, ts=ts, action=action, annotation_type=annotation_type, task_id=task_id, batch_number=batch_number, extra_info=extra_info)
    db.session.add(telemetry)


def save_cglogtask(annotator_id, task_id, batch_number, task_start_time, task_end_time, num_replay_server, num_replay_frontend, action):
    cglogtask = CGLogTask(annotator_id=annotator_id, task_id=task_id, batch_number=batch_number, task_start_time=task_start_time, task_end_time=task_end_time, num_replay_server=num_replay_server, num_replay_frontend=num_replay_frontend, action=action)
    db.session.add(cglogtask)


def save_fglogtask(annotator_id, task_id, batch_number, task_start_time, task_end_time, num_play, num_pause, num_create, num_move, num_resize, num_delete, num_play_region, action):
    fglogtask = FGLogTask(annotator_id=annotator_id, task_id=task_id, batch_number=batch_number, task_start_time=task_start_time, task_end_time=task_end_time, num_play=num_play, num_pause=num_pause, num_create=num_create, num_move=num_move, num_resize=num_resize, num_delete=num_delete, num_play_region=num_play_region, action=action)
    db.session.add(fglogtask)


########### logbatch ###########
# tamoom
def insert_logbatch(batchtable, annotator_id, batch_number, batch_start_time):
    cglogbatchstart = db.session.query(batchtable).filter(
        (batchtable.annotator_id == annotator_id) & (batchtable.batch_number == batch_number)).one()
    # print("cglogbatchstart", cglogbatchstart)
    # print(type(cglogbatchstart), not cglogbatchstart)
    if not cglogbatchstart:
        logbatch = batchtable(annotator_id=annotator_id, batch_number=batch_number, batch_start_time=batch_start_time)
        db.session.add(logbatch)
        # print("------------------- insert log batch --------------------")

# tamoom
def finalize_logbatch(batchtable, annotator_id, batch_number, batch_end_time):
    logbatch = db.session.query(batchtable).filter(batchtable.annotator_id==annotator_id)\
        .filter(batchtable.batch_number == batch_number).one()
    logbatch.batch_end_time = batch_end_time

# tamoom
def update_logbatch_prevclick(batchtable, annotator_id, batch_number):
    logbatch = db.session.query(batchtable).filter(batchtable.annotator_id == annotator_id).filter(
        batchtable.batch_number == batch_number).one()
    logbatch.num_previous_click += 1

# tamoom
def update_logbatch_flag(batchtable, annotator_id, batch_number):
    logbatch = db.session.query(batchtable).filter(batchtable.annotator_id == annotator_id).filter(
        batchtable.batch_number == batch_number).one()
    logbatch.num_flagged += 1


def load_general_info(tasktable, batchtable, patient_names, completed):
    try:
        temp = {}
        for patient in patient_names:
            temp[patient] = [0,0,0,0,0,0] # pass0, pass1, pass2, pass3, is_done, total

        n_total = 0
        n_is_done = 0
        t1 = datetime.utcnow()
        is_dones = db.session.query(tasktable.patient_name, func.count(batchtable.is_done), tasktable.pass_id).join(batchtable, batchtable.task_id == tasktable.id).filter(
            (batchtable.is_done == True), (tasktable.allocated_to!= -1)).group_by(tasktable.patient_name, tasktable.pass_id).all()
        t2 = datetime.utcnow()
        print("is_done:", t2 - t1)
        t1 = datetime.utcnow()
        totals = db.session.query(tasktable.patient_name, func.count(tasktable.id)).group_by(tasktable.patient_name).all()
        t2 = datetime.utcnow()
        print("totals:", t2 - t1)
        for total in totals:
            temp[total[0]][-1]=total[1]
            n_total+=total[1]

        for is_done in is_dones:
            # print(is_done)
            temp[is_done[0]][int(is_done[2])]=is_done[1]
            temp[is_done[0]][-2]+= is_done[1]
            n_is_done+=is_done[1]

        for patient in patient_names:
            if temp[patient]:
                completed[patient].append(temp[patient])
            else:
                completed[patient].append([0,0,0,0,0,0])
        # print(completed)
        return n_is_done, n_total
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
            type(e).__name__) \
             + str(' ') + str(e)
        msg = Message('load_general_info', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return None, None

# get first pass that has count != 0
def get_first_pass():
    fgpassqueue = read_pass_queue()
    first_pass = list(fgpassqueue.keys())[0]
    if fgpassqueue[first_pass]!=0:
        return first_pass
    else:
        return next_pass(first_pass)

# FGPassQueue
def next_pass(pass_id):
    # pass_id  = str(pass_id)
    fgpassqueue = read_pass_queue()
    count = 0
    cursor = list(fgpassqueue.keys()).index(pass_id)
    while count <= len(fgpassqueue):
        # print(list(FGPASSQUEUE.keys()).index(k))
        cursor += 1
        if len(fgpassqueue) == cursor:
            cursor = 0
        if list(fgpassqueue.items())[cursor][1] != 0: # if count is not 0
            return list(fgpassqueue.items())[cursor][0] # return the key i.e pass_id
        count += 1
    return None

def locate_pass_id(fgpassqueue, pass_id):
    for i in range(len(fgpassqueue)):
        if fgpassqueue[i][0] == pass_id:
            return i

def read_pass_queue():
    # read FGPASSQUEUE from the file
    with open('fgpassqueue.json', 'r') as fp:
        fgpassqueue = json.loads(fp.read())
        return OrderedDict(fgpassqueue)

def save_pass_queue(fgpassqueue):
    # save FGPASSQUEUE to a file
    with open('fgpassqueue.json', 'w') as fp:
        fp.write(json.dumps(fgpassqueue))