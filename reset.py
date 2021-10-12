from audio_annotation import db
from audio_annotation.models import User, Patient, CGTask, FGPassHandler, StartTime, FGTask
from datetime import datetime
from collections import OrderedDict
from os import path
from audio_annotation.functions import save_pass_queue, get_first_pass
import pandas as pd
from server_statics import cg_test_initial_true_labels, fg_test_initial_true_labels

def reset_database():
    db.session.rollback()
    try:
        no_delete = ['patient', 'audio_file', 'non_silent_segment', 'cg_segment', 'cg_task', 'user']
        meta = db.metadata
        for table in reversed(meta.sorted_tables):
            if table.name not in no_delete:
                print('Clear table %s' % table)
                db.session.execute('TRUNCATE TABLE ' + table.name + ' RESTART IDENTITY CASCADE')

        db.session.commit()
        print("done dropping all tables")
        reset_CGTask()  # set allocated_to == None
        reset_FGpasshandler()
        print("before")
        reset_StartTime()
        print("after")
        if not path.exists("fgpassqueue.json"):
            print("fg pass queue does not exist trying to create a default one ...")
            save_pass_queue(OrderedDict({'0': 4, '1': 3, '2': 2, '3': 1}))

        # reset cglabels and fglabels
        df = pd.DataFrame(
            columns=['task_id', 'patient_name', 'audiofile_id', 'cgsegment_id', 'submit_time', 'annotator', 'batch_number', 'pass_id',
                     'label', 'submit_time'])
        df.to_csv('CGLabels.csv', mode='w')

        df = pd.DataFrame(
            columns=['task_id', 'patient_name', 'audiofile_id', 'cgsegment_id', 'submit_time', 'annotator','batch_number', 'sample_rate',
                     'pass_id',
                     'label', 'start', 'end', 'submit_time'])
        df.to_csv('FGLabels.csv', mode='w')
        create_cg_test(cg_test_initial_true_labels.keys())
        create_fg_test(fg_test_initial_true_labels.keys())
          
    except Exception as e:
        db.session.rollback()
        raise

def add_fgtasks_for_test_server():
    cgtasks = db.session.query(CGTask).limit(5).all()
    for cgtask in cgtasks:
        fgtask = FGTask(cgsegment_id=cgtask.cgsegment_id, audiofile_id=cgtask.audiofile_id,
                        patient_name=cgtask.patient_name,
                        start_time_audiofile=cgtask.start_time_audiofile, start_time_seg=cgtask.start_time_seg,
                        start_time=cgtask.start_time, sample_rate=cgtask.sample_rate, pass_id='0')
        db.session.add(fgtask)
    db.session.commit()
    for cgtask in cgtasks:
        fgtask = FGTask(cgsegment_id=cgtask.cgsegment_id, audiofile_id=cgtask.audiofile_id,
                        patient_name=cgtask.patient_name,
                        start_time_audiofile=cgtask.start_time_audiofile, start_time_seg=cgtask.start_time_seg,
                        start_time=cgtask.start_time, sample_rate=cgtask.sample_rate, pass_id='1')
        db.session.add(fgtask)
    db.session.commit()
    for cgtask in cgtasks:
        fgtask = FGTask(cgsegment_id=cgtask.cgsegment_id, audiofile_id=cgtask.audiofile_id,
                        patient_name=cgtask.patient_name,
                        start_time_audiofile=cgtask.start_time_audiofile, start_time_seg=cgtask.start_time_seg,
                        start_time=cgtask.start_time, sample_rate=cgtask.sample_rate, pass_id='2')
        db.session.add(fgtask)
    db.session.commit()
    for cgtask in cgtasks:
        fgtask = FGTask(cgsegment_id=cgtask.cgsegment_id, audiofile_id=cgtask.audiofile_id,
                        patient_name=cgtask.patient_name,
                        start_time_audiofile=cgtask.start_time_audiofile, start_time_seg=cgtask.start_time_seg,
                        start_time=cgtask.start_time, sample_rate=cgtask.sample_rate, pass_id='3')
        db.session.add(fgtask)
    db.session.commit()


# run this when you want to change test segments or during initialization
def create_cg_test(cgsegment_ids):
    cgtask_ids = []
    for segment in cgsegment_ids:
        tasks = db.session.query(CGTask).filter(CGTask.cgsegment_id == segment).order_by(CGTask.id).all()
        for task in tasks:
            task.allocated_to = -1
        cgtask_ids.append(tasks[0].id)
    db.session.commit()
    return cgtask_ids

# run this when you want to change test segments or during initialization
def create_fg_test(fgsegment_ids):
    fgtask_ids = []
    for segment in fgsegment_ids:
        tasks = db.session.query(CGTask).filter(CGTask.cgsegment_id == segment).order_by(CGTask.id).all()
        for task in tasks:
            task.allocated_to = -1
        fgtask = FGTask(cgsegment_id=tasks[0].cgsegment_id, audiofile_id=tasks[0].audiofile_id,
                        patient_name=tasks[0].patient_name,
                        start_time_audiofile=tasks[0].start_time_audiofile, start_time_seg=tasks[0].start_time_seg,
                        start_time=tasks[0].start_time, sample_rate=tasks[0].sample_rate, pass_id='0', allocated_to=-1)
        db.session.add(fgtask)
        db.session.flush()
        fgtask_ids.append(fgtask.id)

    db.session.commit()
    return fgtask_ids


def reset_CGTask():
    t1 = datetime.now()
    CGTask.query.update({CGTask.allocated_to: None})
    db.session.commit()
    t2 = datetime.now()
    print("Reset in ", t2 - t1)


def reset_FGTask():
    t1 = datetime.now()
    FGTask.query.update({FGTask.allocated_to: None})
    db.session.commit()
    t2 = datetime.now()
    print("Reset in ", t2 - t1)


def drop_FGBatch():
    try:
        db.session.execute('TRUNCATE TABLE fg_batch RESTART IDENTITY CASCADE')
        db.session.commit()
    except Exception as e:
        print(str(e))


def drop_FGTask():
    try:
        db.session.execute('TRUNCATE TABLE fg_task RESTART IDENTITY CASCADE')
        db.session.commit()
    except Exception as e:
        print(str(e))


def drop_user():
    db.session.execute('TRUNCATE TABLE "user" RESTART IDENTITY CASCADE')
    db.session.commit()


def reset_FGpasshandler():
    db.session.execute('TRUNCATE TABLE fg_pass_handler RESTART IDENTITY CASCADE')
    db.session.commit()

    user_ids = db.session.query(User.id).filter(User.role == 'annotator').filter(User.status == 'active').all()
    user_ids = [r[0] for r in user_ids]
    for usr in user_ids:
        fgpasshandler = FGPassHandler(annotator_id=usr, pass_number=get_first_pass(), count=0)
        db.session.add(fgpasshandler)
    db.session.commit()

def reset_StartTime():
    patients = db.session.query(Patient.name).all()
    print("patients", patients)
    patients = [r[0] for r in patients]
    types = ['cg', 'fg']
    for patient in patients:
        print("resetign starttime")
        for t in types:
            starttime = StartTime(annotationtype=t, patient_name=patient, base_time=datetime(1970, 1, 1, 1, 1, 1, 1))
            db.session.add(starttime)
    db.session.commit()

def get_table_rows(table):
    print(db.session.query(table).count())
