from flask import session, render_template, flash, request, jsonify
from audio_annotation import app, db, cgworkallocator, fgworkallocator, mail
from flask_login import current_user, login_required
from audio_annotation.decorators import annotator_required
from audio_annotation.models import FGTask, CGBatch, CGLabel, CGFlag, CGLogBatch
from server_statics import FG_NUM_REPT, fgDict, cg_test_initial
from datetime import datetime
from audio_annotation.functions import save_telemetry, save_cglogtask, finalize_logbatch, \
    update_logbatch_prevclick, update_logbatch_flag, insert_flag, get_latest_flag, select_task_in_batch, \
    latest_num_in_batch
import pandas as pd
from flask_mail import Message
import os, sys
from threading import Lock

lock = Lock()

################ functions ##################
def save_label_coarse(batchrow, label, annotator_id, submit_time): # tamoom
    cglabel = CGLabel(task_id=batchrow.task_id, batch_number=batchrow.batch_number, label=label, annotator_id=annotator_id, submit_time=submit_time)
    db.session.add(cglabel)
    pd.DataFrame([[batchrow.task_id, batchrow.cgtask.patient_name, batchrow.cgtask.audiofile_id,
                   batchrow.cgtask.cgsegment_id, submit_time, annotator_id, batchrow.batch_number,
                   batchrow.cgtask.pass_id, label, submit_time]]) \
        .to_csv('CGLabels.csv', mode='a', header=False)

def cg_get_label(task_id, batch_number, annotator_id): # tamoom
    prev_label = db.session.query(CGLabel)\
        .filter((CGLabel.task_id == task_id) & (CGLabel.batch_number == batch_number) & (CGLabel.annotator_id == annotator_id))\
        .order_by(CGLabel.submit_time.desc()).first()
    prev_flag = get_latest_flag(CGFlag, task_id, current_user.id, batch_number)
    description = None
    if prev_flag == None and prev_label == None:
        return None, None
    else:
        if prev_flag == None:
            labeled = prev_label.label
        else:
            if prev_label:
                # check which one is newer:
                if prev_label.submit_time > prev_flag.submit_time:
                    labeled = prev_label.label
                else:
                    labeled = 'flag'
                    description = prev_flag.description
            else:
                labeled = 'flag'
                description = prev_flag.description
    return labeled, description


def cg_get_annotations_so_far(batch_number, current_task_id, annotator_id): # tamoom
    previous_labels_so_far = []
    annotations_in_current_batch = db.session.query(CGBatch).filter(CGBatch.annotator_id == current_user.id) \
        .filter(CGBatch.batch_number == batch_number).order_by(
        CGBatch.num_in_batch.asc()).all()
    for task in annotations_in_current_batch:
        if task.task_id == current_task_id:  # for current task just insert 'current' in list
            previous_labels_so_far.append('current')
        else:
            labeled, description = cg_get_label(task.task_id, batch_number, annotator_id)  # labeled = true or false or flag or None   description = None or value
            previous_labels_so_far.append(labeled)
    return previous_labels_so_far

def add_fgtask(cgsegment_id, audiofile_id, patient_name, start_time_audiofile, start_time_seg, start_time, sample_rate): # tamoom
    # probably need to set fgtask segment_id index in db
    # check if already exists, don't add duplicates to fgtask
    check = db.session.query(FGTask).filter(FGTask.cgsegment_id == cgsegment_id).all()
    if not check: # if check is empty (Add fgtasks if they are not already in the fgtask table)
        for r in range(FG_NUM_REPT):
            for p in fgDict.keys():
                fgtask = FGTask(cgsegment_id=cgsegment_id, audiofile_id=audiofile_id, patient_name=patient_name,
                                start_time_audiofile=start_time_audiofile, start_time_seg=start_time_seg,
                                start_time=start_time, sample_rate=sample_rate, pass_id=p)
                db.session.add(fgtask)

        for p in fgDict.keys(): # for each pass, add to allocation dictionary
            fgworkallocator.add_to_allocations(cgsegment_id, p, FG_NUM_REPT)
    else:
        print("fgtask already exists, so won't add it again to fgtask", cgsegment_id)

def remove_fgtask(cgsegment_id): # tamoom
    # check if can actually delete
    tasks = db.session.query(FGTask.id).filter(FGTask.cgsegment_id == cgsegment_id).filter(
        FGTask.allocated_to != None).all()
    if not tasks:  # remove only if all the tasks have not been asign to anyone yet
        db.session.query(FGTask.id).filter(FGTask.cgsegment_id == cgsegment_id).filter(
            FGTask.allocated_to == None).delete()
        for p in fgDict.keys():
            fgworkallocator.remove_from_allocations(cgsegment_id, p)

def cg_initialize_sessions():
    session['cg-taskStartTime'] = datetime.now()
    session['cg-numReplay'] = 0


############################################   ROUTES   ####################################################
@app.route("/coarseGrainedAnnotation", methods=["GET", "POST"])
@login_required
@annotator_required
def coarseGrainedAnnotation():
    cg_initialize_sessions()
    try:
        save_telemetry(annotator_id=current_user.id, ts=datetime.now(), action='coarse-grained-btn',
                       annotation_type='cg')
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(type(e).__name__)\
             + str(' ') + str(e) + ' userid: ' + str(current_user.id)

        msg = Message('/coarseGrainedAnnotation/', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)

    return render_template('coarseGrainedAnnotation.html')


@app.route("/coarseGrainedAnnotation/getNextFileInfo/", methods=["GET"])
@login_required
def get_next_file_info_coarse():
    with lock:
        try:
            cg_initialize_sessions()
            cg_batch = db.session.query(CGBatch).filter(CGBatch.annotator_id == current_user.id).filter(
                CGBatch.is_done == False).order_by(
                CGBatch.num_in_batch.asc()).first()
            if cg_batch is None:
                # try to create a batch
                cg_batch = cgworkallocator.create_batch(annotator_id=current_user.id)  # either returns None or a json
                if cg_batch is None:
                    return 'There is no file left for now. Thank you for your effort!'

            previous_labels_so_far= cg_get_annotations_so_far(cg_batch.batch_number, cg_batch.task_id, current_user.id)
            db.session.commit()

            return jsonify({"num_in_batch": cg_batch.num_in_batch, "batch_id": cg_batch.id, "task_id": cg_batch.task_id,
                            "batch_size": cg_batch.batch_size, "batch_number": cg_batch.batch_number,
                            "cgsegment_id": cg_batch.cgtask.cgsegment_id, "audiofile_id": cg_batch.cgtask.audiofile_id,
                            "patient_name": cg_batch.cgtask.patient_name, "previous_labels_so_far": previous_labels_so_far})
        except Exception as e:
            db.session.rollback()
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
                type(e).__name__) \
                 + str(' ') + str(e) + ' userid: ' + str(current_user.id)

            msg = Message('/coarseGrainedAnnotation/getNextFileInfo/', sender=os.environ['EMAIL_SENDER'],
                          recipients=[os.environ['EMAIL_RECEIVER']],
                          body=er)
            mail.send(msg)

            return 'There was a problem fetching the file, please try again.'


@app.route("/coarseGrainedAnnotation/getPreviousFileInfo/", methods=["GET"])
@login_required
def get_previous_file_info_coarse():
    with lock:
        try:
            session['cg-previous'] = True
            cgbatch_number = int(request.args.get('batch_number'))
            num_in_batch = int(request.args.get('num_in_batch'))
            current_task = int(request.args.get('current_task'))

            cg_batch = db.session.query(CGBatch).filter(CGBatch.annotator_id == current_user.id).filter(
                CGBatch.batch_number == cgbatch_number).filter(
                CGBatch.num_in_batch == num_in_batch).one()  # Return exactly one result or raise an exception.
            if cg_batch is None:
                return 'There was a problem fetching the file, please try later.'

            if cg_batch.is_done == False:
                check_previous_task_status = db.session.query(CGBatch).filter(
                    CGBatch.annotator_id == current_user.id).filter(
                    CGBatch.batch_number == cgbatch_number).filter(CGBatch.num_in_batch == (num_in_batch - 1)).one()
                if check_previous_task_status.is_done == False:  # it means the previous batch has not been annotated yet so they cant go to this task
                    return 'You cannot go to this task because it is not annotated yet!'

            # if session.pop('cg-previous', None) == True:  # it means that they didn't submit the previous annotation
            save_cglogtask(annotator_id=current_user.id, task_id=current_task, batch_number=cgbatch_number,
                           task_start_time=session.pop('cg-taskStartTime', None), task_end_time=datetime.now(),
                           num_replay_server=session.pop('cg-numReplay', None), num_replay_frontend=-1, action='view')
            cg_initialize_sessions()
            save_telemetry(annotator_id=current_user.id, ts=session['cg-taskStartTime'], action='previous-btn', annotation_type='cg',
                           task_id=current_task, batch_number=cgbatch_number, extra_info=cg_batch.task_id)

            update_logbatch_prevclick(CGLogBatch, current_user.id, cgbatch_number)

            latest = latest_num_in_batch(CGBatch, current_user.id, cgbatch_number)
            previous_labels_so_far = cg_get_annotations_so_far(cg_batch.batch_number, cg_batch.task_id, current_user.id)
            labeled, description = cg_get_label(cg_batch.task_id, cg_batch.batch_number, current_user.id)
            db.session.commit()
            # get the most recent label

            return jsonify({"latest": latest[0], "num_in_batch": cg_batch.num_in_batch, "batch_id": cg_batch.id,
                            "task_id": cg_batch.task_id, "batch_size": cg_batch.batch_size,
                            "batch_number": cg_batch.batch_number, "cgsegment_id": cg_batch.cgtask.cgsegment_id,
                            "audiofile_id": cg_batch.cgtask.audiofile_id, "patient_name": cg_batch.cgtask.patient_name,
                            "description": description, "labeled": labeled, "previous_labels_so_far": previous_labels_so_far
                            })
        except Exception as e:
            db.session.rollback()
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
                type(e).__name__) \
                 + str(' ') + str(e) + ' userid: ' + str(current_user.id)

            msg = Message('/coarseGrainedAnnotation/getPreviousFileInfo/', sender=os.environ['EMAIL_SENDER'],
                          recipients=[os.environ['EMAIL_RECEIVER']],
                          body=er)
            mail.send(msg)
            return 'There was a problem fetching the file, please try again.'




@app.route("/coarseGrainedAnnotation/flagFile", methods=["POST"])
@login_required
def flag_file_coarse():
    try:
        data = request.get_json()
        description = data["description"]
        batch_id = data["batch_id"]
        num_in_batch = data.pop("num_in_batch")
        batch_number = data.pop("batch_number")

        submit_time = datetime.now()

        select_row = select_task_in_batch(CGBatch, batch_id, current_user.id, num_in_batch, batch_number)
        if select_row == None:
            return jsonify({'msg': 'failed'})
        select_row.is_done = True

        insert_flag(CGFlag, select_row.task_id, description, current_user.id, batch_number, submit_time)

        save_telemetry(annotator_id=current_user.id, ts=submit_time, action='flag-btn', annotation_type='cg',
                       task_id=select_row.task_id, batch_number=batch_number)

        update_logbatch_flag(CGLogBatch, current_user.id, batch_number)
        cg_initialize_sessions()

        latest = latest_num_in_batch(CGBatch, current_user.id, batch_number)

        db.session.commit()

        if (num_in_batch == select_row.batch_size) or latest[0] == select_row.batch_size:
            finalize_logbatch(CGLogBatch, current_user.id, batch_number, submit_time)
            previous_labels_so_far = cg_get_annotations_so_far(batch_number, None, current_user.id)
            db.session.commit()
            return jsonify({'msg': 'last_task', 'previous_labels_so_far': previous_labels_so_far})

        return jsonify({'msg': 'success'})
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(type(e).__name__) \
             + str(' ') + str(e) + ' userid: ' + str(current_user.id)

        msg = Message('/coarseGrainedAnnotation/flagFile', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return jsonify({'msg': 'Something went wrong with the server, please try again. Sorry for this inconvenience.'})


@app.route("/coarseGrainedAnnotation/submitAnnotation", methods=["POST"])
@login_required
def submit_annotation_coarse():
    with lock:
        try:
            data = request.get_json()
            label = data.pop("label")
            batch_id = data.pop("batch_id")
            num_in_batch = data.pop("num_in_batch")
            batch_number = data.pop("batch_number")
            cgsegment_id = data.pop("cgsegment_id")

            submit_time = datetime.now()

            select_row = select_task_in_batch(CGBatch, batch_id, current_user.id, num_in_batch, batch_number)
            if select_row == None:
                db.session.rollback()
                msg = Message('/coarseGrainedAnnotation/submitAnnotation', sender=os.environ['EMAIL_SENDER'],
                              recipients=[os.environ['EMAIL_RECEIVER']],
                              body=f'select row is None! for annotator: {current_user.id}')
                mail.send(msg)
                flash(u'Oops! Something went wrong with the server!', 'error')
                return jsonify(
                    {'msg': 'Something went wrong with the server, please try again. Sorry for this inconvenience.'})

            if select_row.task_id not in cg_test_initial:
                # add or remove fgtask based on previous annotation only if it is not in the test segments
                if select_row.is_done == True: # this file has been annotated before, so load the most recent annotation label (label_tuple[0])
                    # get the most recent label
                    label_tuple = db.session.query(CGLabel.label).filter(CGLabel.task_id == select_row.task_id).order_by(
                        CGLabel.submit_time.desc()).first()
                    if label == True:  # the new label is True, check the old label
                        if label_tuple is None or label_tuple[0] == False:  # it was previously flagged or False, add it to fgtask table
                            # if is_cgsegment_in_fgtask(cgsegment_id) == False:
                            add_fgtask(cgsegment_id, select_row.cgtask.audiofile_id, select_row.cgtask.patient_name,
                                       select_row.cgtask.start_time_audiofile, select_row.cgtask.start_time_seg,
                                       select_row.cgtask.start_time, select_row.cgtask.sample_rate)
                        else:  # the old label is True
                            # if previously labeled true by this person, then don't add it another time to the fgtask table, just add it to cglabel, cglog
                            pass

                    else:  # the new label is False, check the old label
                        if label_tuple is None or label_tuple[0] == False:  # it was previously flagged or False! and because the new label is false, no need to add it to fgtask table
                            pass
                        else:  # the old label is True
                            # remove fgtask
                            # if is_cgsegment_in_fgtask(cgsegment_id) == True:
                            remove_fgtask(cgsegment_id)

                else:  # if it is a new annotation
                    select_row.is_done = True
                    if label == True:
                        # if is_cgsegment_in_fgtask(cgsegment_id) == False: # only add it if nobody else has add it to fgtask
                        add_fgtask(cgsegment_id, select_row.cgtask.audiofile_id, select_row.cgtask.patient_name,
                                   select_row.cgtask.start_time_audiofile, select_row.cgtask.start_time_seg,
                                   select_row.cgtask.start_time, select_row.cgtask.sample_rate)
            else: # if it is a test task
                select_row.is_done = True
            save_label_coarse(batchrow=select_row, label=label, annotator_id=current_user.id, submit_time=submit_time)


            action = 'yes-btn' if label == 1 else 'no-btn'
            save_telemetry(annotator_id=current_user.id, ts=submit_time, action=action, annotation_type='cg',
                           task_id=select_row.task_id, batch_number=batch_number)

            save_cglogtask(annotator_id=current_user.id, task_id=select_row.task_id, batch_number=batch_number,
                           task_start_time=session.pop('cg-taskStartTime', None), task_end_time=submit_time,
                           num_replay_server=session.pop('cg-numReplay', None), num_replay_frontend=data['numReplay'],
                           action='submit')

            cg_initialize_sessions()
            session['cg-previous'] = False

            latest = latest_num_in_batch(CGBatch, current_user.id, batch_number)
       
            if (num_in_batch == select_row.batch_size) or latest[0] == select_row.batch_size: # if it is the last task in the batch
                finalize_logbatch(CGLogBatch, current_user.id, batch_number, submit_time)
                previous_labels_so_far = cg_get_annotations_so_far(batch_number, None, current_user.id)
                db.session.commit()
                return jsonify({'msg': 'last_task', 'latest': latest[0], 'previous_labels_so_far': previous_labels_so_far})

            db.session.commit()
            return jsonify({'msg': 'success'})
        except Exception as e:
            db.session.rollback()
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
                type(e).__name__) \
                 + str(' ') + str(e) + ' userid: ' + str(current_user.id)

            msg = Message('/coarseGrainedAnnotation/submitAnnotation', sender=os.environ['EMAIL_SENDER'],
                          recipients=[os.environ['EMAIL_RECEIVER']],
                          body=er)
            mail.send(msg)
            return jsonify({'msg': 'Something went wrong with the server, please try again. Sorry for this inconvenience.'})