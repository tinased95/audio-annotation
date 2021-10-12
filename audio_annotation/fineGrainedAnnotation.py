from flask import session, render_template, flash, request, jsonify
from audio_annotation import app, db, fgworkallocator, mail
from flask_login import current_user, login_required

from audio_annotation.decorators import annotator_required
from audio_annotation.models import FGBatch, FGLabel, FGFlag, FGLogBatch, FGTask
from sqlalchemy.sql import func
from server_statics import fgDict
from datetime import datetime
from audio_annotation.functions import save_telemetry, save_fglogtask, \
    insert_logbatch, finalize_logbatch, update_logbatch_prevclick, update_logbatch_flag, insert_flag, get_latest_flag, \
    select_task_in_batch, latest_num_in_batch
import pandas as pd
from flask_mail import Message
import os, sys
from threading import Lock

lock = Lock()

################ functions ##################
def save_label_fine(batchrow, label, start, end, submit_time, sample_rate, annotator_id):
    fglabel = FGLabel(task_id=batchrow.task_id, batch_number=batchrow.batch_number, label=label, start=start, end=end, submit_time=submit_time, annotator_id=annotator_id)
    db.session.add(fglabel)
    pd.DataFrame([[batchrow.task_id, batchrow.fgtask.patient_name, batchrow.fgtask.audiofile_id,
                   batchrow.fgtask.cgsegment_id, submit_time, annotator_id, batchrow.batch_number, sample_rate,
                   batchrow.fgtask.pass_id, start, end, label, submit_time]]) \
        .to_csv('FGLabels.csv', mode='a', header=False)

def fg_get_labels(task_id, batch_number, annotator_id): # tamoom
    prev_labels = db.session.query(FGLabel.submit_time, func.count(FGLabel.submit_time)).filter(
            (FGLabel.task_id == task_id) & (FGLabel.batch_number == batch_number) & (FGLabel.annotator_id == annotator_id))\
        .group_by(FGLabel.submit_time).order_by(FGLabel.submit_time.desc()).first()
    if prev_labels:
        fglabels_recent = db.session.query(FGLabel).filter(FGLabel.submit_time == prev_labels.submit_time).first()
    prev_flag = get_latest_flag(FGFlag, task_id, current_user.id, batch_number)
    description = None
    if prev_flag == None and prev_labels == None:
        return None, None
    else:
        if prev_flag == None: # it means that there is label
            labeled = False if fglabels_recent.label == 'no label' else True
        else: # it may be both flagged and labeld or just flagged
            if prev_labels:
                # check which one is newer:
                if fglabels_recent.submit_time > prev_flag.submit_time:
                    labeled = False if fglabels_recent.label == 'no label' else True
                else:
                    labeled = 'flag'
                    description = prev_flag.description
            else:
                labeled = 'flag'
                description = prev_flag.description
    return labeled, description

def fg_get_annotations_so_far(batch_number, current_task_id, annotator_id): # tamoom
    previous_labels_so_far = []
    annotations_in_current_batch = db.session.query(FGBatch).filter(FGBatch.annotator_id == current_user.id) \
        .filter(FGBatch.batch_number == batch_number).order_by(
        FGBatch.num_in_batch.asc()).all()
    for task in annotations_in_current_batch:
        if task.task_id == current_task_id:  # for current task just insert 'current' in list
            previous_labels_so_far.append('current')
        else:
            labeled, description = fg_get_labels(task.task_id, batch_number, annotator_id)  # labeled = true or false or flag or None   description = None or value
            previous_labels_so_far.append(labeled)
    return previous_labels_so_far


def get_speech_annotations(fg_batch):
    speech_annotations = {}
    fgtask_id, = db.session.query(FGTask.id).filter(
        (FGTask.pass_id == '0') & (FGTask.cgsegment_id == fg_batch.fgtask.cgsegment_id)).order_by(
        FGTask.id).first()
    # print("fgtask_id", fgtask_id)
    fg_speech_labels = db.session.query(FGLabel.submit_time, func.count(FGLabel.submit_time)).filter(
        (FGLabel.task_id == fgtask_id)).group_by(
        FGLabel.submit_time, FGLabel.batch_number).order_by(
        FGLabel.submit_time.asc()).first()  # get the first set of labels from the first repertition
    if fg_speech_labels == None:
        msg = Message('/fineGrainedAnnotation/get_speech_annotations', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=f'There is no speech labels for the pass_id=3. This happened for user_id: {current_user.id}')
        mail.send(msg)
    # speech_annotations = {}
    if fg_speech_labels:  # this is because there might be no annotation for speech pass
        fglabels_recent = db.session.query(FGLabel).filter(
            FGLabel.submit_time == fg_speech_labels.submit_time).all()
        sample_rate = fg_batch.fgtask.sample_rate
        for fglabel_recent in fglabels_recent:
            if fglabel_recent.label == 'no label':
                speech_annotations = []
            elif fglabel_recent.label in speech_annotations:
                speech_annotations[fglabel_recent.label].append(
                    {"start": fglabel_recent.start / sample_rate, "end": fglabel_recent.end / sample_rate})
            else:
                speech_annotations[fglabel_recent.label] = []
                speech_annotations[fglabel_recent.label].append(
                    {"start": fglabel_recent.start / sample_rate, "end": fglabel_recent.end / sample_rate})
        # print(fglabel_recent)
        # print("annotations", speech_annotations)
    # else:
    #     print("no fg pass labels for this file")
    return speech_annotations


def fg_initialize_sessions():
    session['fg-taskStartTime'] = datetime.now()
    session['fg-numPlay'] = 0
    session['fg-numPause'] = 0
    session['fg-numDelete'] = 0
    session['fg-numCreate'] = 0
    session['fg-numMove'] = 0
    session['fg-numResize'] = 0
    session['fg-numPlayRegion'] = 0


############################################   ROUTES   ####################################################

@app.route("/fineGrainedAnnotation")
@login_required
@annotator_required
def fineGrainedAnnotation():
    fg_initialize_sessions()
    try:
        save_telemetry(annotator_id=current_user.id, ts=datetime.now(), action='fine-grained-btn', annotation_type='fg')
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(fname) + str(exc_tb.tb_lineno) + str(type(e).__name__) + str(e)

        msg = Message('/fineGrainedAnnotation/', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
    return render_template('fineGrainedAnnotation.html')


@app.route("/fineGrainedAnnotation/getNextFileInfo/", methods=["GET"])
@login_required
def get_next_file_info():
    with lock:
        # print("##########load next file#################")
        try:
            fg_initialize_sessions()
            fg_batch = db.session.query(FGBatch).filter(FGBatch.annotator_id == current_user.id).filter(
                FGBatch.is_done == False).order_by(
                FGBatch.num_in_batch.asc()).first()
            if fg_batch is None:
                # try to create a batch
                print("FGBatch not found, trying to create one!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                fg_batch = fgworkallocator.create_batch(
                    annotator_id=current_user.id)  # either returns null or resurn a json

                print("created with batch", fg_batch)
                if fg_batch is None:
                    print("fgbatch is none")
                    return 'There is no file left for now. Thank you for your effort!'
                # insert_logbatch(FGLogBatch, current_user.id, fg_batch.batch_number, session['fg-taskStartTime'])
            previous_labels_so_far = fg_get_annotations_so_far(fg_batch.batch_number, fg_batch.task_id, current_user.id)

            # print(fgDict[fg_batch.fgtask.pass_id]['instructions'])
            if session['pop-up-instructions'] == True:
                popup = True
                session['pop-up-instructions'] = False
            else:
                popup = False

            speech_annotations = {}
            if fg_batch.fgtask.pass_id == '3':
                speech_annotations = get_speech_annotations(fg_batch)
            
            db.session.commit()
            return jsonify({"num_in_batch": fg_batch.num_in_batch, "batch_id": fg_batch.id, "task_id": fg_batch.task_id,
                            "batch_size": fg_batch.batch_size, "batch_number": fg_batch.batch_number,
                            "cgsegment_id": fg_batch.fgtask.cgsegment_id, "audiofile_id": fg_batch.fgtask.audiofile_id,
                            "patient_name": fg_batch.fgtask.patient_name,
                            "instructions": fgDict[fg_batch.fgtask.pass_id]['instructions'],
                            "annotationTag": fgDict[fg_batch.fgtask.pass_id]['annotationTag'],
                            "visualization": fgDict[fg_batch.fgtask.pass_id]['visualization'],
                            "popup": popup, 'previous_labels_so_far': previous_labels_so_far, "pass_id": fg_batch.fgtask.pass_id, 'speech_annotations': speech_annotations
                            })
        except Exception as e:
            print(str(e))
            db.session.rollback()
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
                type(e).__name__) \
                 + str(' ') + str(e) + ' userid: ' + str(current_user.id)
            msg = Message('/fineGrainedAnnotation/getNextFileInfo/', sender=os.environ['EMAIL_SENDER'],
                          recipients=[os.environ['EMAIL_RECEIVER']],
                          body=er)
            mail.send(msg)
            return 'There was a problem fetching the file, please try again.'





@app.route("/fineGrainedAnnotation/getPreviousFileInfo/", methods=["GET"])
@login_required
def get_previous_file_info_fine():
    with lock:
        try:
            session['fg-previous'] = True
            fgbatch_number = int(request.args.get('batch_number'))
            num_in_batch = int(request.args.get('num_in_batch'))
            current_task = int(request.args.get('current_task'))
            # print(fgbatch_number, num_in_batch, current_task)
            fg_batch = db.session.query(FGBatch).filter(FGBatch.annotator_id == current_user.id).filter(
                FGBatch.batch_number == fgbatch_number).filter(
                FGBatch.num_in_batch == num_in_batch).one()  # Return exactly one result or raise an exception.
            # print(fg_batch)
            if fg_batch is None:
                # print("fg batch is empty!!")
                return 'There was a problem fetching the file, please try later.'

            if fg_batch.is_done == False:
                check_previous_task_status = db.session.query(FGBatch).filter(
                    FGBatch.annotator_id == current_user.id).filter(
                    FGBatch.batch_number == fgbatch_number).filter(FGBatch.num_in_batch == (num_in_batch - 1)).one()
                # print(check_previous_task_status)
                if check_previous_task_status.is_done == False:  # it means the previous batch has not been annotated yet so they cant go to this task
                    return 'You cannot go to this task because it is not annotated yet!'

            # if session.pop('fg-previous', None) == True:  # it means that they didn't submit the annotation
            save_fglogtask(annotator_id=current_user.id, task_id=current_task, batch_number=fgbatch_number,
                           task_start_time=session.pop('fg-taskStartTime', None), task_end_time=datetime.now(),
                           num_play=session['fg-numPlay'], num_pause=session['fg-numPause'],
                           num_create=session['fg-numCreate'], num_move=session['fg-numMove'],
                           num_resize=session['fg-numResize'], num_delete=session['fg-numDelete'],
                           num_play_region=session['fg-numPlayRegion'], action='view')

            # The last is_done == True
            fg_initialize_sessions()
            save_telemetry(annotator_id=current_user.id, ts=session['fg-taskStartTime'], action='previous-btn', annotation_type='fg',
                           task_id=current_task, batch_number=fgbatch_number, extra_info=fg_batch.task_id)
            update_logbatch_prevclick(FGLogBatch, current_user.id, fgbatch_number)

            latest = latest_num_in_batch(FGBatch, current_user.id, fgbatch_number)
                # db.session.query(FGBatch.num_in_batch).filter(FGBatch.annotator_id == current_user.id).filter(
                # FGBatch.batch_number == fgbatch_number).filter(FGBatch.is_done == True).order_by(
                # FGBatch.num_in_batch.desc()).first()

            # prev_flag = get_latest_flag(FGFlag, fg_batch.task_id, current_user.id, fgbatch_number)
            # description = prev_flag.description if prev_flag else ''

            previous_labels_so_far = fg_get_annotations_so_far(fg_batch.batch_number, fg_batch.task_id, current_user.id)
            labeled, description = fg_get_labels(fg_batch.task_id, fg_batch.batch_number, current_user.id)

            speech_annotations = {}
            if fg_batch.fgtask.pass_id == '3':
                speech_annotations = get_speech_annotations(fg_batch)
                # print("speech_annotations", speech_annotations)

            db.session.commit()

            return jsonify({"latest": latest[0], "num_in_batch": fg_batch.num_in_batch, "batch_id": fg_batch.id,
                            "task_id": fg_batch.task_id, "batch_size": fg_batch.batch_size,
                            "batch_number": fg_batch.batch_number, "cgsegment_id": fg_batch.fgtask.cgsegment_id,
                            "audiofile_id": fg_batch.fgtask.audiofile_id, "patient_name": fg_batch.fgtask.patient_name,
                            "instructions": fgDict[fg_batch.fgtask.pass_id]['instructions'],
                            "annotationTag": fgDict[fg_batch.fgtask.pass_id]['annotationTag'],
                            "visualization": fgDict[fg_batch.fgtask.pass_id]['visualization'],
                            "description": description, 'previous_labels_so_far': previous_labels_so_far,
                            "pass_id": fg_batch.fgtask.pass_id, 'speech_annotations': speech_annotations})
        except Exception as e:
            db.session.rollback()
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
                type(e).__name__) \
                 + str(' ') + str(e) + ' userid: ' + str(current_user.id)

            msg = Message('/fineGrainedAnnotation/getPreviousFileInfo/', sender=os.environ['EMAIL_SENDER'],
                          recipients=[os.environ['EMAIL_RECEIVER']],
                          body=er)
            mail.send(msg)
            return 'There was a problem fetching the file, please try again.'

@app.route("/fineGrainedAnnotation/flagFile", methods=["POST"])
@login_required
def flag_file_fine():
    try:
        data = request.get_json()
        description = data["description"]
        batch_id = data["batch_id"]
        num_in_batch = data.pop("num_in_batch")
        batch_number = data.pop("batch_number")

        submit_time = datetime.now()

        select_row = select_task_in_batch(FGBatch, batch_id, current_user.id, num_in_batch, batch_number)
            # db.session.query(FGBatch).filter(FGBatch.id == batch_id).filter(
            # FGBatch.annotator_id == current_user.id).filter(
            # FGBatch.num_in_batch == num_in_batch).filter(FGBatch.batch_number == batch_number).one()

        if select_row == None:
            return jsonify({'msg': 'failed'})
        ### got info from js and now I want to save it in cgflag table
        select_row.is_done = True

        insert_flag(FGFlag, select_row.task_id, description, current_user.id, batch_number, submit_time)

        save_telemetry(annotator_id=current_user.id, ts=submit_time, action='flag-btn', annotation_type='fg',
                       task_id=select_row.task_id, batch_number=batch_number)
        update_logbatch_flag(FGLogBatch, current_user.id, batch_number)

        fg_initialize_sessions()
        latest = latest_num_in_batch(FGBatch, current_user.id, batch_number)
            # db.session.query(FGBatch.num_in_batch).filter(FGBatch.annotator_id == current_user.id).filter(
            # FGBatch.batch_number == batch_number).filter(FGBatch.is_done == True).order_by(
            # FGBatch.num_in_batch.desc()).first()

        db.session.commit()

        if (num_in_batch == select_row.batch_size) or latest[0] == select_row.batch_size:
            finalize_logbatch(FGLogBatch, current_user.id, batch_number, submit_time)
            previous_labels_so_far = fg_get_annotations_so_far(batch_number, None, current_user.id)
            db.session.commit()
            return jsonify({'msg': 'last_task', 'previous_labels_so_far': previous_labels_so_far})

        if num_in_batch == select_row.batch_size:
            return jsonify({'msg': 'last_task'})
        return jsonify({'msg': 'success'})
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(type(e).__name__) \
             + str(' ') + str(e) + ' userid: ' + str(current_user.id)

        msg = Message('/fineGrainedAnnotation/flagFile', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return jsonify({'msg': 'Something went wrong with the server, please try again. Sorry for this inconvenience.'})

@app.route("/fineGrainedAnnotation/getAnnotations", methods=["GET"])
@login_required
def get_annotations():
    try:
        fgbatch_number = int(request.args.get('batch_number'))
        num_in_batch = int(request.args.get('num_in_batch'))

        # batch_id = int(request.args.get('batch_id'))

        fgbatch = db.session.query(FGBatch).filter(FGBatch.annotator_id == current_user.id)\
            .filter(FGBatch.batch_number == fgbatch_number).filter(FGBatch.num_in_batch == num_in_batch).first()

        sample_rate = fgbatch.fgtask.cgsegment.nonsilentsegment.audiofile.sample_rate
        fgtask_id = fgbatch.task_id

        fglabels = db.session.query(FGLabel.submit_time, func.count(FGLabel.submit_time)).filter(
            (FGLabel.task_id == fgtask_id) & (FGLabel.batch_number == fgbatch_number)& (FGLabel.annotator_id == current_user.id))\
            .group_by(FGLabel.submit_time)\
            .order_by(FGLabel.submit_time.desc()).all()
        prev_flag = get_latest_flag(FGFlag, fgtask_id, current_user.id, fgbatch_number)
        annotations = {}
        # the last element in the list is the newest set of labels
        if fglabels:
            fglabels_recent = db.session.query(FGLabel).filter(FGLabel.submit_time == fglabels[0][0]).all()
            if prev_flag:
                if fglabels_recent[0].submit_time > prev_flag.submit_time:
                    for fglabel_recent in fglabels_recent:
                        if fglabel_recent.label == 'no label':
                            annotations = []
                            return jsonify(annotations)
                        elif fglabel_recent.label in annotations:
                            annotations[fglabel_recent.label].append(
                                {"start": fglabel_recent.start / sample_rate, "end": fglabel_recent.end / sample_rate})
                        else:
                            annotations[fglabel_recent.label] = []
                            annotations[fglabel_recent.label].append(
                                {"start": fglabel_recent.start / sample_rate, "end": fglabel_recent.end / sample_rate})
            else:
                for fglabel_recent in fglabels_recent:
                    if fglabel_recent.label == 'no label':
                        annotations = []
                        return jsonify(annotations)
                    elif fglabel_recent.label in annotations:
                        annotations[fglabel_recent.label].append(
                            {"start": fglabel_recent.start / sample_rate, "end": fglabel_recent.end / sample_rate})
                    else:
                        annotations[fglabel_recent.label] = []
                        annotations[fglabel_recent.label].append(
                            {"start": fglabel_recent.start / sample_rate, "end": fglabel_recent.end / sample_rate})

        return jsonify(annotations)
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(type(e).__name__) \
             + str(' ') + str(e) + ' userid: ' + str(current_user.id)

        msg = Message('/fineGrainedAnnotation/getAnnotations', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return jsonify({'msg': 'Something went wrong with the server, please try again. Sorry for this inconvenience.'})

@app.route("/fineGrainedAnnotation/submitAnnotation", methods=["POST"])
@login_required
def submit_annotation_fine():
    try:
        data = request.get_json()
        batch_id = data.pop("batch_id")
        num_in_batch = data.pop("num_in_batch")
        batch_number = data.pop("batch_number")
        # everything else in data is content

        submit_time = datetime.now()

        select_row = select_task_in_batch(FGBatch, batch_id, current_user.id, num_in_batch, batch_number)
        sample_rate = select_row.fgtask.cgsegment.nonsilentsegment.audiofile.sample_rate

        if select_row == None:
            db.session.rollback()
            msg = Message('/fineGrainedAnnotation/submitAnnotation', sender=os.environ['EMAIL_SENDER'],
                          recipients=[os.environ['EMAIL_RECEIVER']],
                          body=f'select row is None! for annotator: {current_user.id}')
            mail.send(msg)
            flash(u'Oops! Something went wrong with the server!', 'error')
            return jsonify(
                {'msg': 'Something went wrong with the server, please try again. Sorry for this inconvenience.'})

        select_row.is_done = True
        # add labels to FGLabel
        if not data["annotations"]:  # no labels
            save_label_fine(batchrow=select_row, label='no label', start=0, end=0, submit_time=submit_time,
                            sample_rate=sample_rate, annotator_id=current_user.id)
        else:
            for label in data["annotations"]:
                save_label_fine(batchrow=select_row, label=label['annotation'], start=label['start'] * sample_rate,
                                end=label['end'] * sample_rate, submit_time=submit_time, sample_rate=sample_rate, annotator_id=current_user.id)

        save_telemetry(annotator_id=current_user.id, ts=submit_time, action='submit-btn', annotation_type='fg',
                       task_id=select_row.task_id, batch_number=batch_number)
        save_fglogtask(annotator_id=current_user.id, task_id=select_row.task_id, batch_number=batch_number,
                       task_start_time=session.pop('fg-taskStartTime', None), task_end_time=submit_time,
                       num_play=session['fg-numPlay'], num_pause=session['fg-numPause'], num_create=session['fg-numCreate'],
                       num_move=session['fg-numMove'], num_resize=session['fg-numResize'],
                       num_delete=session['fg-numDelete'], num_play_region=session['fg-numPlayRegion'], action='submit')

        fg_initialize_sessions()
        session['fg-previous'] = False
        latest = latest_num_in_batch(FGBatch, current_user.id, batch_number)

        # print(num_in_batch, select_row.batch_size)
        # print(latest[0], select_row.batch_size)
        if (num_in_batch == select_row.batch_size) or latest[0] == select_row.batch_size:  # if it is the last task in the batch
            finalize_logbatch(FGLogBatch, current_user.id, batch_number, submit_time)
            previous_labels_so_far = fg_get_annotations_so_far(batch_number, None, current_user.id)
            db.session.commit()
            return jsonify({'msg': 'last_task', 'latest': latest[0], 'previous_labels_so_far': previous_labels_so_far})

        db.session.commit()
        return jsonify({'msg': 'success'})
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(type(e).__name__) \
             + str(' ') + str(e) + ' userid: ' + str(current_user.id)

        msg = Message('/fineGrainedAnnotation/submitAnnotation', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return jsonify({'msg': 'Something went wrong with the server, please try again. Sorry for this inconvenience.'})