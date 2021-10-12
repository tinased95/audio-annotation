from audio_annotation import db
from audio_annotation.functions import get_latest_flag
from audio_annotation.models import *
import pandas as pd
from sqlalchemy import func


# proccessed_labels = pd.DataFrame(columns=['task_id', 'annotator_id', 'batch_number', 'start', 'end', 'label'])
def fg_get_labels(task_id, batch_number, annotator_id):
    fglabels = db.session.query(FGLabel.submit_time, func.count(FGLabel.submit_time)).filter(
        (FGLabel.task_id == task_id) & (FGLabel.batch_number == batch_number) & (
                    FGLabel.annotator_id == annotator_id)) \
        .group_by(FGLabel.submit_time) \
        .order_by(FGLabel.submit_time.desc()).all()
    prev_flag = get_latest_flag(FGFlag, task_id, annotator_id, batch_number)
    annotations = {}
    # the last element in the list is the newest set of labels
    if fglabels:
        fglabels_recent = db.session.query(FGLabel).filter(FGLabel.submit_time == fglabels[0][0]).all()
        if prev_flag:
            if fglabels_recent[0].submit_time > prev_flag.submit_time:
                for fglabel_recent in fglabels_recent:
                    if fglabel_recent.label == 'no label':
                        annotations = []
                        return annotations
                    elif fglabel_recent.label in annotations:
                        pd.DataFrame([[task_id,annotator_id, batch_number,fglabel_recent.start,fglabel_recent.end, fglabel_recent.label]]).to_csv('tt.csv', mode='a', header=False)
                        annotations[fglabel_recent.label].append(
                            {"start": fglabel_recent.start / 16000, "end": fglabel_recent.end / 16000})
                    else:
                        pd.DataFrame([[task_id, annotator_id, batch_number, fglabel_recent.start, fglabel_recent.end,
                                       fglabel_recent.label]]).to_csv('tt.csv', mode='a', header=False)
                        annotations[fglabel_recent.label] = []
                        annotations[fglabel_recent.label].append(
                            {"start": fglabel_recent.start / 16000, "end": fglabel_recent.end / 16000})
        else:
            for fglabel_recent in fglabels_recent:
                if fglabel_recent.label == 'no label':
                    annotations = []
                    return annotations
                elif fglabel_recent.label in annotations:
                    pd.DataFrame([[task_id, annotator_id, batch_number, fglabel_recent.start, fglabel_recent.end,
                                   fglabel_recent.label]]).to_csv('tt.csv', mode='a', header=False)
                    annotations[fglabel_recent.label].append(
                        {"start": fglabel_recent.start / 16000, "end": fglabel_recent.end / 16000})
                else:
                    pd.DataFrame([[task_id, annotator_id, batch_number, fglabel_recent.start, fglabel_recent.end,
                                   fglabel_recent.label]]).to_csv('tt.csv', mode='a', header=False)
                    annotations[fglabel_recent.label] = []
                    annotations[fglabel_recent.label].append(
                        {"start": fglabel_recent.start / 16000, "end": fglabel_recent.end / 16000})
    return annotations


def cg_get_labels(task_id, batch_number, annotator_id):
    cglabels = db.session.query(CGLabel.submit_time, func.count(CGLabel.submit_time)).filter(
        (CGLabel.task_id == task_id) & (CGLabel.batch_number == batch_number) & (
                    CGLabel.annotator_id == annotator_id)) \
        .group_by(CGLabel.submit_time) \
        .order_by(CGLabel.submit_time.desc()).all()
    prev_flag = get_latest_flag(CGFlag, task_id, annotator_id, batch_number)
    annotations = {}
    # the last element in the list is the newest set of labels
    if cglabels:
        cglabels_recent = db.session.query(CGLabel).filter(CGLabel.submit_time == cglabels[0][0]).all()
        if prev_flag:
            if cglabels_recent[0].submit_time > prev_flag.submit_time:
                for cglabel_recent in cglabels_recent:
                    pd.DataFrame([[task_id, annotator_id, batch_number, cglabel_recent.label]]).to_csv('tt.csv', mode='a', header=False)
        else:
            for cglabel_recent in cglabels_recent:
                pd.DataFrame([[task_id,annotator_id, batch_number, cglabel_recent.label]]).to_csv('tt.csv', mode='a', header=False)
    return annotations


###### FG
tasks = db.session.query(FGBatch).filter((FGBatch.is_done ==True) & (FGBatch.annotator_id == 11)).all()
df = pd.DataFrame(
            columns=['task_id', 'annotator_id', 'batch_number', 'start', 'end', 'label'])
df.to_csv('tt.csv', mode='w')
for task in tasks:
    fg_get_labels(task.task_id, task.batch_number, task.annotator_id)

###### CG
tasks = db.session.query(CGBatch).filter((CGBatch.is_done ==True) & (CGBatch.annotator_id == 11)).all()
df = pd.DataFrame(
            columns=['task_id', 'annotator_id', 'batch_number', 'start', 'end', 'label'])
df.to_csv('tt.csv', mode='w')
for task in tasks:
    cg_get_labels(task.task_id, task.batch_number, task.annotator_id)