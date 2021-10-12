from audio_annotation import db, cgworkallocator, fgworkallocator
from audio_annotation.models import User, CGBatch, CGTask, Patient, FGBatch, FGTask
from tqdm import tqdm
import random
import pandas as pd
import logging
from datetime import datetime
import matplotlib.pyplot as plt
from audio_annotation.coarseGrainedAnnotation import add_fgtask
from server_statics import fgDict


def creation_time_over_time():
    file1 = open('fgbatch.log', 'r')
    lines = file1.read().split('\n')
    lines = lines[:-1]

    def get_time(line):
        for i in line.split(','):
            x = i.split('=')
            if x[0] == ' time':
                return x[1]

    list_of_times = []
    for l in tqdm(lines):
        t = datetime.strptime(get_time(l), '%H:%M:%S.%f').time()
        list_of_times.append((t.hour * 60 + t.minute) * 60 + t.second + (t.microsecond / 1000000))
    print(sum(list_of_times)/len(list_of_times), min(list_of_times), max(list_of_times))
    fig = plt.figure(figsize=(8, 6))
    plt.hist(list_of_times, bins='auto')

    # ax = plt.axes()
    # plt.bar(range(3600), list_of_times[0:3600])
    # plt.xlabel('Progress')
    # plt.ylabel('Batch creation time in seconds')
    plt.show()
    fig.savefig('fg_creation_time2.png')


def check_cgduplicates():
    user_ids = db.session.query(User.id).filter(User.role == 'annotator').filter(User.status == 'active').all()
    user_ids = [r[0] for r in user_ids]
    for ann in user_ids:
        tasks = pd.read_sql(db.session.query(CGTask).filter(CGTask.annotator_id == ann).statement, db.session.bind)
        duplicateRows = tasks[tasks.duplicated(['cgsegment_id', 'start_time'])]
        if duplicateRows.empty:
            print("Passed!", ann)
        else:
            print("Failed!", ann)


def check_fgduplicates():
    user_ids = db.session.query(User.id).filter(User.role == 'annotator').filter(User.status == 'active').all()
    user_ids = [r[0] for r in user_ids]
    for ann in user_ids:
        tasks = pd.read_sql(db.session.query(FGTask).filter(FGTask.annotator_id == ann).statement, db.session.bind)
        duplicateRows = tasks[tasks.duplicated(['cgsegment_id', 'pass_id', 'start_time'])]
        if duplicateRows.empty:
            print("Passed!", ann)
        else:
            print(duplicateRows)
            print("Failed!", ann)


# check_duplicates()
# creation_time_over_time()


def check_cgprogress(): 
    cgbatches = db.session.query(CGBatch).all()
    patient_names = db.session.query(Patient.name).all()
    patient_names = [r[0] for r in patient_names]

    completed = {}
    for p in patient_names:
        completed[p] = 0
    for row in cgbatches:
        if row.is_done:
            completed[row.cgtask.patient_name] += 1
    cgworkallocator.checkpoint.info(completed)
    return completed


def check_fgprogress(): 
    fgbatches = db.session.query(FGBatch).all()
    patient_names = db.session.query(Patient.name).all()
    patient_names = [r[0] for r in patient_names]

    completed = {}
    for p in patient_names:
        completed[p] = 0
    for row in fgbatches:
        if row.is_done:
            completed[row.fgtask.patient_name] += 1
    fgworkallocator.checkpoint.info(completed)
    return completed





def annotate_fgbatch(ids):
    # print('annotate_fgbatch...')
    db.session.query(FGBatch).filter(
        FGBatch.task_id.in_(ids)
    ).update({
        FGBatch.is_done: True
    }, synchronize_session=False)

    # db.session.commit()


def test_cg_create_batch():
    user_ids = db.session.query(User.id).filter(User.role == 'annotator').filter(User.status == 'active').all()
    user_ids = [r[0] for r in user_ids]
    for x in tqdm(range(43200)):  # 12hours
        ids = cgworkallocator.create_batch(annotator_id=random.choice(user_ids))  # assign tasks to annotator
        annotate_cgbatch(ids)  # make them done
        if x % 300 == 0:
            check_cgprogress()


def create_dummy_fgtasks():
    # db.engine.execute('TRUNCATE TABLE fg_task RESTART IDENTITY CASCADE')
    label = [0, 1, 2, 3, 4]
    cgtasks = db.session.query(CGTask).limit(500000).distinct(CGTask.cgsegment_id)
    for cgtask in tqdm(cgtasks):
        if random.choice(label) == 1:  # 1/5
            try:
                add_fgtask(cgtask.cgsegment_id, cgtask.audiofile_id, cgtask.patient_name, cgtask.start_time_audiofile,
                           cgtask.start_time_seg, cgtask.start_time, cgtask.sample_rate)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(str(e))


def create_all_fgtasks():  # to run over all fgtasks
    cgtasks = db.session.query(CGTask).distinct(CGTask.cgsegment_id).all()
    print(len(cgtasks))
    # try:
    fgtasks = []
    count = 0
    for cgtask in tqdm(cgtasks):
        count += 1
        for r in range(2):
            for p in fgDict.keys():
                fgtasks.append(FGTask(cgsegment_id=cgtask.cgsegment_id, audiofile_id=cgtask.audiofile_id,
                                      patient_name=cgtask.patient_name,
                                      start_time_audiofile=cgtask.start_time_audiofile,
                                      start_time_seg=cgtask.start_time_seg,
                                      start_time=cgtask.start_time, sample_rate=cgtask.sample_rate,
                                      pass_id=p))

        if count % 100000 == 1:
            try:
                db.session.bulk_save_objects(fgtasks)
                db.session.commit()
                fgtasks = []
            except Exception as e:
                db.session.rollback()
                print(str(e))

    db.session.bulk_save_objects(fgtasks)
    db.session.commit()
    # except Exception as e:
    #     db.session.rollback()
    #     print(str(e))


def make_them_complete():
    try:
        ids = fgworkallocator.create_batch(annotator_id=7)  # assign tasks to annotator
        # print("heeeeee")
        # print("hhh", ids)
        annotate_fgbatch(ids)  # make them done
    except Exception as e:
        print(str(e))


def test_fg_create_batch():
    user_ids = db.session.query(User.id).filter(User.role == 'annotator').filter(User.status == 'active').all()
    user_ids = [r[0] for r in user_ids]

    for x in tqdm(range(400000)): 
        try:
            an = random.choice(user_ids)
            ids = fgworkallocator.create_batch(annotator_id=an)  # assign tasks to annotator
            annotate_fgbatch(ids) 
            db.session.commit()
        except Exception as e:
            print("error!!!!")
            print(str(e))


def create_blacklist():
    user_ids = db.session.query(User.id).filter(User.role == 'annotator').filter(User.status == 'active').all()
    user_ids = [r[0] for r in user_ids]
    for usr in user_ids:
        cgworkallocator.add_to_blacklist(usr)

def final_test_cg_batch():
    user_ids = db.session.query(User.id).filter(User.role == 'annotator').filter(User.status == 'active').all()
    user_ids = [r[0] for r in user_ids]
    for i in range(100):
        an = random.choice(user_ids)
        for i in range(60):
            before = len(cgworkallocator.blacklist[an]['0'])
            ids = db.session.query(CGBatch.task_id).filter(CGBatch.annotator_id == an).filter(
                CGBatch.is_done == False).order_by(
                CGBatch.num_in_batch.asc()).all()
            if ids != None:
                ids = [r[0] for r in ids]
                annotate_cgbatch(ids, an)
            t = datetime.utcnow()
            cgworkallocator.create_batch(annotator_id=an)
            after= len(cgworkallocator.blacklist[an]['0'])
            print(f"ann: {an}, before: {before}, after: {after}, time: {datetime.utcnow() - t}")


def annotate_cgbatch(ids, annotator_id):
    db.session.query(CGBatch).filter(
        CGBatch.task_id.in_(ids)
    ).filter(CGBatch.annotator_id == annotator_id).update({
        CGBatch.is_done: True
    }, synchronize_session=False)
    db.session.commit()

# from audio_annotation import app, db, cgworkallocator
# from audio_annotation.models import *
# import random


# user = User(firstname='a', lastname='a', email='a@a.com',password='123',status='active', role='annotator', is_temp_pw=False)
# db.session.add(user)
# user = User(firstname='b', lastname='b', email='b@b.com',password='123',status='active', role='annotator', is_temp_pw=False)
# db.session.add(user)
# user = User(firstname='c', lastname='c', email='c@c.com',password='123',status='active', role='annotator', is_temp_pw=False)
# db.session.add(user)
# user = User(firstname='d', lastname='d', email='d@d.com',password='123',status='active', role='annotator', is_temp_pw=False)
# db.session.add(user)
# user = User(firstname='e', lastname='e', email='e@e.com',password='123',status='active', role='annotator', is_temp_pw=False)
# db.session.add(user)
# user = User(firstname='f', lastname='f', email='f@f.com',password='123',status='active', role='annotator', is_temp_pw=False)
# db.session.add(user)
# user = User(firstname='g', lastname='g', email='g@g.com',password='123',status='active', role='annotator', is_temp_pw=False)
# db.session.add(user)
# user = User(firstname='h', lastname='h', email='h@h.com',password='123',status='active', role='annotator', is_temp_pw=False)
# db.session.add(user)
# db.session.commit()
# user_ids = db.session.query(User.id).filter(User.role == 'annotator').filter(User.status == 'active').all()
# user_ids = [r[0] for r in user_ids]
# for usr in user_ids:
#     cgworkallocator.add_to_blacklist(usr)

# db.session.commit()