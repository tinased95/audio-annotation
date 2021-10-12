from flask import render_template, url_for, flash, redirect, request
from audio_annotation import app, db, bcrypt, cgworkallocator, fgworkallocator, mail
from audio_annotation.functions import load_general_info, get_first_pass, get_latest_labels, calc_jaccard_index_initial
from audio_annotation.decorators import admin_required
from audio_annotation.models import User, Patient, CGTask, FGTask, \
    CGBatch, FGBatch, CGLabel, FGLabel, CGFlag, FGFlag, FGLogTask, CGLogBatch, FGLogBatch, \
    UserActivity, StartTime, FGPassHandler, CGLogTask, WorkProgress, Telemetry
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import random
import string
import io
from flask import Response
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from flask_mail import Message
import sys, os
from sqlalchemy import func, and_
from server_statics import cg_test_initial, fg_test_initial
from datetime import datetime, timedelta


def get_task_info(patient, annotationtype):
    if annotationtype == 'cg':
        tasktable, batchtable = CGTask, CGBatch
    else:
        tasktable, batchtable = FGTask, FGBatch
    tasks = pd.read_sql(db.session
                        .query(tasktable.id, tasktable.start_time, tasktable.allocated_to, batchtable.is_done)
                        .join(batchtable, isouter=True)
                        .filter(tasktable.patient_name == patient)
                        .order_by(tasktable.start_time).statement, db.session.bind)
    if tasks.empty:
        return [], [], [], [], None

    tasks.set_index('start_time', inplace=True)
    out = tasks['allocated_to'].resample('D').agg([lambda x: x.isna().sum(), 'size'])

    out.columns = ['nans', 'total']

    finished = tasks['is_done'].resample('D').agg(['sum'])
    finished = finished['sum']

    ratio = (sum(finished) / sum(out['total'])) * 100

    return out.index.strftime('%Y-%m-%d').values, out['nans'], out['total'] - out['nans'] - finished, finished, ratio


def get_logtasks(annotator_id, freq, logtasktable, start_date, end_date):
    logtasks = pd.read_sql(db.session
                           .query(logtasktable.id, logtasktable.task_id, logtasktable.task_start_time,
                                  logtasktable.task_end_time, logtasktable.action)
                           .filter((logtasktable.annotator_id == annotator_id) &
                                   (logtasktable.task_start_time >= start_date) & (
                                           logtasktable.task_end_time <= end_date))
                           .order_by(logtasktable.task_start_time).statement, db.session.bind)

    if logtasks.empty:
        return [], [], [], 0, 0

    logtasks['duration'] = (logtasks['task_end_time'] - logtasks['task_start_time']).dt.total_seconds()

    logtasks_submitted = logtasks[logtasks['action'] == 'submit']
    summary = logtasks_submitted.groupby('task_id').agg({'task_start_time': ['min'], 'duration': 'sum'})
    summary.columns = ['task_start_time', 'duration']
    avg_time_per_task = round(summary['duration'].mean(), 2)  # tamoom
    summary.set_index('task_start_time', inplace=True)
    out = summary['duration'].resample(freq).agg(['size', 'sum'])
    out.columns = ['annotated', 'duration']

    return out.index.strftime('%Y-%m-%d %H:%M:%S').values, \
           out['annotated'], \
           out['duration'], \
           avg_time_per_task, \
           len(logtasks[logtasks['action'] == 'view'])


def get_all_annotators_in_one_graph(freq, logtasktable):
    logtasks = pd.read_sql(db.session
                           .query(logtasktable.id, logtasktable.task_id, logtasktable.task_start_time,
                                  logtasktable.task_end_time, logtasktable.action, logtasktable.annotator_id)
                           .order_by(logtasktable.task_start_time).statement, db.session.bind)

    if logtasks.empty:
        return [], [], [], 0, 0

    logtasks['duration'] = (logtasks['task_end_time'] - logtasks['task_start_time']).dt.total_seconds()
    logtasks_submitted = logtasks[logtasks['action'] == 'submit']
    annotators = logtasks_submitted['annotator_id'].unique()
    annotator_dict = {}
    for ann in annotators:
        annotator_tasks = logtasks_submitted[logtasks_submitted.annotator_id == ann]
        summary = annotator_tasks.groupby('task_id').agg({'task_start_time': 'min', 'duration': 'sum'})
        summary.columns = ['task_start_time', 'duration']
        summary.set_index('task_start_time', inplace=True)
        out = summary['duration'].resample(freq).agg(['size', 'sum'])
        out.columns = ['annotated', 'duration']
        out.index = out.index.strftime('%Y-%m-%d %H:%M:%S')
        out = out.to_records(index=True)
        result = list(out)
        annotator_dict[ann] = result  # list of tuples (num_allocations, duration)

    logtasks_submitted.set_index('task_start_time', inplace=True)
    return annotator_dict, logtasks_submitted['duration'].resample(freq).agg(['size', 'sum']).index.strftime(
        '%Y-%m-%d %H:%M:%S').values  # annotator_dict[ann_id] = [(num_allocations, duration)]


def get_logbatches(annotator_id, logbatchtable, flagtable, tasktable):
    logbatch = pd.read_sql(
        db.session.query(logbatchtable).filter(logbatchtable.annotator_id == annotator_id)
            .filter(logbatchtable.batch_end_time != None).statement, db.session.bind)
    flags = db.session.query(flagtable, tasktable).join(tasktable).filter(tasktable.allocated_to == annotator_id).all()
    return len(flags)  # logbatch['num_previous_click'].sum(),


@app.route("/admin")
@admin_required
def admin_page():
    # *** I do not count test segments in the number of tasks done
    try:
        patient_names = db.session.query(Patient.name).all()
        patient_names = [r[0] for r in patient_names]
        completed = {}
        for patient in patient_names:
            completed[patient] = []
        # CG
        cg_finished, cg_total = load_general_info(CGTask, CGBatch, patient_names, completed)
        # FG
        # print("Now processing FG ...")
        fg_finished, fg_total = load_general_info(FGTask, FGBatch, patient_names, completed)
        # print(fg_finished)
        users = db.session.query(User).filter(User.role == 'annotator').filter(User.status == 'active').count()
        # db.session.commit()
        pass_colors = ['bg-success', 'bg-warning', 'bg-info', 'bg-danger']
        return render_template('admin.html', users=users, cg_finished=cg_finished, fg_finished=fg_finished,
                               cg_total=cg_total, fg_total=fg_total, completed=completed, pass_colors=pass_colors)
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
            type(e).__name__) \
             + str(' ') + str(e)
        msg = Message('/admin', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return render_template('admin.html', users=[], cg_finished=None, fg_finished=None,
                               cg_total=None, fg_total=None, completed=None)


@app.route('/admin/tasks_progress', methods=['GET'])
@admin_required
def tasks_progress():
    try:
        patient_names = db.session.query(Patient.name).all()
        patient_names = [r[0] for r in patient_names]
        patient = request.args.get('patient')
        annotationtype = request.args.get('annotationtype', None)
        if patient is None:
            patient = patient_names[0]
        labels, falses, trues, finished, ratio = get_task_info(patient, annotationtype)

        info = {'patient': patient, 'ratio': ratio}
        return render_template('tasks_progress.html', labels=labels, falses=falses, trues=trues, finished=finished,
                               patient_names=patient_names, annotationtype=annotationtype, info=info)
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
            type(e).__name__) \
             + str(' ') + str(e)
        msg = Message('/admin/tasks_progress', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return render_template('tasks_progress.html', labels=None, falses=None, trues=None, finished=None,
                               patient_names=None, annotationtype=None, info=None)


@app.route('/admin/annotators_progress', methods=['GET'])
@admin_required
def annotators_progress():
    try:
        frequencies = {'H': 'Hour', 'T': 'Minute', 'D': 'Day'}
        annotators = db.session.query(User.id, User.firstname, User.lastname).filter(User.role == 'annotator').filter(
            User.status == 'active').all()
        ann_id = request.args.get('annotator')
        freq = request.args.get('freq')
        annotationtype = request.args.get('annotationtype')

        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)
        # print("dates: ",start_date, end_date)
        if not annotators:
            return render_template('annotators_progress.html', labels=[], freq=freq,
                                   annotationtype=annotationtype, start_date=start_date, end_date=end_date,
                                   annotated=[], annotators=annotators, num_stay_connected=0,
                                   duration=[], frequencies=frequencies, n_total=0,
                                   avg_task=0, n_previous=0,
                                   n_flagged=0, loginlogouts=0, task_time=0,
                                   info={'ann_info': 0})
        if not start_date:
            start_date = datetime(2020, 11, 11, 1, 1, 1, 1).strftime('%Y-%m-%dT%H:%M:%S')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        if ann_id == None:
            ann_id = annotators[0][0]  # get the first annotator_id
        if freq == None:
            freq = 'H'
        if annotationtype == None:
            annotationtype = 'cg'
        ann_info = [ann for ann in annotators if ann.id == int(ann_id)]  # get firstname, lastname by searching id
        assert len(ann_info) == 1, len(ann_info)

        if annotationtype == 'cg':
            logtasktable, logbatchtable, flagtable, tasktable, batchtable, labeltable = CGLogTask, CGLogBatch, CGFlag, CGTask, CGBatch, CGLabel
        else:
            logtasktable, logbatchtable, flagtable, tasktable, batchtable, labeltable = FGLogTask, FGLogBatch, FGFlag, FGTask, FGBatch, FGLabel
        # print("updated dates: ", start_date, end_date)
        xticks, num_annotations, durations, avg_time_per_task, n_previous_clicks = get_logtasks(ann_id, freq,
                                                                                                logtasktable,
                                                                                                start_date, end_date)

        subq = db.session.query(
            flagtable.task_id,
            func.max(flagtable.submit_time).label('maxdate')
        ).group_by(flagtable.task_id).subquery('t1')

        flag_query = db.session.query(flagtable).join(
            subq,
            and_(
                flagtable.task_id == subq.c.task_id,
                flagtable.submit_time == subq.c.maxdate,
                flagtable.annotator_id == ann_id
            )
        ).all()

        n_flagged = 0
        for k in flag_query:
            label = db.session.query(labeltable).filter(labeltable.task_id == k.task_id).order_by(
                labeltable.submit_time.desc()).first()
            if label:
                if label.submit_time < k.submit_time:
                    n_flagged += 1
            else:
                n_flagged += 1

        total_num_annotations_check = db.session.query(batchtable).filter(batchtable.annotator_id == ann_id).filter(
            batchtable.is_done == True).count()

        loginlogouts = get_login_logout_times(start_date, end_date, ann_id)
        num_stay_connected = retrieve_telemetry(ann_id, start_date, end_date, 'stay-connected-btn', annotationtype)

        return render_template('annotators_progress.html', xticks=xticks, freq=freq,
                               annotationtype=annotationtype, start_date=start_date, end_date=end_date,
                               num_annotations=num_annotations, annotators=annotators,
                               durations=durations, frequencies=frequencies,
                               num_files_annotated=sum(num_annotations), num_stay_connected=num_stay_connected,
                               total_num_annotations_check=total_num_annotations_check,
                               avg_time_per_task=avg_time_per_task, n_previous_clicks=n_previous_clicks,
                               n_flagged=n_flagged, loginlogouts=loginlogouts,
                               task_time=str(timedelta(seconds=sum(durations))),
                               info={'ann_info': ann_info[0]})

    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
            type(e).__name__) \
             + str(' ') + str(e)
        msg = Message('/admin/annotators_progress', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return render_template('annotators_progress.html', xticks=None, freq=None,
                               annotationtype=None, num_annotations=None, annotators=None,
                               durations=None, frequencies=None,
                               num_files_annotated=sum(None), num_stay_connected=None,
                               total_num_annotations_check=None,
                               avg_time_per_task=None, n_previous_clicks=None,
                               n_flagged=None, loginlogouts=None, task_time=None,
                               info={'ann_info': None})


def retrieve_telemetry(annotator_id, start_date, end_date, action, annotation_type):
    return db.session.query(Telemetry).filter((Telemetry.annotator_id == annotator_id)
                                              & (Telemetry.ts >= start_date) & (Telemetry.ts <= end_date)
                                              & (Telemetry.action == action)) \
        .filter(Telemetry.annotation_type == annotation_type).count()


def get_login_logout_times(start_date, end_date, user_id):
    loginlogouts = pd.read_sql(db.session.query(UserActivity) \
                               .filter((UserActivity.user_id == user_id) & (UserActivity.logout_time != None)) \
                               .filter(
        (UserActivity.login_time >= start_date) & (UserActivity.login_time <= end_date)).statement, db.session.bind)
    if loginlogouts.empty:
        return '0:0:0'
    loginlogouts['duration'] = (loginlogouts['logout_time'] - loginlogouts['login_time']).dt.total_seconds()
    return str(timedelta(seconds=sum(loginlogouts['duration'])))


@app.route('/admin/annotators_in_one_graph', methods=['GET'])
@admin_required
def annotators_in_one_graph():
    frequencies = {'H': 'Hour', 'T': 'Minute', 'D': 'Day'}
    freq = request.args.get('freq')
    annotationtype = request.args.get('annotationtype')
    if freq == None:
        freq = 'D'
    if annotationtype == None:
        annotationtype = 'cg'
    if annotationtype == 'cg':
        logtasktable = CGLogTask
    else:
        logtasktable = FGLogTask

    annotators_dict, xticks = get_all_annotators_in_one_graph(freq, logtasktable)
    return render_template('annotators_in_one_graph.html', xticks=xticks, freq=freq, frequencies=frequencies,
                           annotationtype=annotationtype, annotators_dict=annotators_dict)


###############################
# manage users #
@app.route("/admin/users")
@admin_required
def manage_users():
    try:
        all_data = db.session.query(User).all()
        return render_template("users.html", users=all_data)
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
            type(e).__name__) \
             + str(' ') + str(e)
        msg = Message('/admin/users', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return render_template("users.html", users=[])


# insert data to mysql database via html forms
@app.route('/insertuser', methods=['POST'])
@admin_required
def insert_user():
    if request.method == 'POST':
        try:
            firstname = request.form['firstname']
            lastname = request.form['lastname']
            email = request.form['email']
            password = request.form['password']
            status = request.form['status']
            role = request.form['role']
            is_temp_pw = True if request.form.getlist('is_temp_pw') else False

            if is_temp_pw == True:
                letters_and_digits = string.ascii_letters + string.digits
                generated_pass = ''.join((random.choice(letters_and_digits) for i in range(5)))
                passw = bcrypt.generate_password_hash(generated_pass).decode('utf-8')
                flash("Password is: " + generated_pass)
            else:
                passw = bcrypt.generate_password_hash(password).decode('utf-8')
                flash("Password is: " + password)
            user = User(firstname=firstname, lastname=lastname, email=email,
                        password=passw,
                        status=status, role=role, is_temp_pw=is_temp_pw)

            db.session.add(user)
            db.session.flush()
            if role == 'annotator':
                pass_num = get_first_pass()
                if not db.session.query(FGPassHandler).filter(FGPassHandler.annotator_id == user.id).all():
                    fgpasshandler = FGPassHandler(annotator_id=user.id, pass_number=pass_num, count=0)
                    db.session.add(fgpasshandler)

                cgworkallocator.add_to_blacklist(user.id)
                fgworkallocator.add_to_blacklist(user.id)

            db.session.commit()
            flash("User Inserted Successfully")
            return redirect(url_for('manage_users'))
        except Exception as e:
            db.session.rollback()
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
                type(e).__name__) \
                 + str(' ') + str(e)
            flash("User Insertion Failed! ", str(er))
            return redirect(url_for('manage_users'))


# update user
@app.route('/updateuser', methods=['GET', 'POST'])
@admin_required
def update_user():
    if request.method == 'POST':
        try:
            user = User.query.get(request.form.get('id'))
            user.firstname = request.form['firstname']
            user.lastname = request.form['lastname']
            user.email = request.form['email']
            user.role = request.form['role']
            user.is_temp_pw = True if request.form.getlist('is_temp_pw') else False
            db.session.commit()
            flash("User Updated Successfully")
            return redirect(url_for('manage_users'))
        except Exception as e:
            db.session.rollback()
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
                type(e).__name__) \
                 + str(' ') + str(e)
            flash("User Update Failed! ", str(er))
            return redirect(url_for('manage_users'))


# deactivate user
@app.route('/deactivateuser/<id>/', methods=['GET', 'POST'])
@admin_required
def deactivate_user(id):
    try:
        user = User.query.get(id)
        user.status = 'inactive'  # so that they can't login anymore
        user.session_token = None
        db.session.commit()
        flash("User Deactivated Successfully")
        return redirect(url_for('manage_users'))
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
            type(e).__name__) \
             + str(' ') + str(e)
        flash("User Deactivation Failed! ", str(er))
        return redirect(url_for('manage_users'))


# activate user
@app.route('/activateuser/<id>/', methods=['GET', 'POST'])
@admin_required
def activate_user(id):
    try:
        user = User.query.get(id)
        user.status = 'active'
        db.session.commit()
        flash("User Activated Successfully")
        return redirect(url_for('manage_users'))
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
            type(e).__name__) \
             + str(' ') + str(e)
        flash("User Activation Failed! ", str(er))
        return redirect(url_for('manage_users'))


# reset password
@app.route('/resetpass/<id>/', methods=['GET', 'POST'])
@admin_required
def reset_pass(id):
    try:
        letters_and_digits = string.ascii_letters + string.digits
        generated_pass = ''.join((random.choice(letters_and_digits) for i in range(5)))
        user = User.query.get(id)
        user.is_temp_pw = True
        user.session_token = None
        user.password = bcrypt.generate_password_hash(generated_pass).decode('utf-8')
        db.session.commit()
        flash("New password is: " + generated_pass)
        return redirect(url_for('manage_users'))
    except Exception as e:
        db.session.rollback()
        flash("Reset Password Failed! ")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(fname) + str(exc_tb.tb_lineno) + str(type(e).__name__) + str(e)
        msg = Message('/resetpass/<id>/', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return redirect(url_for('manage_users'))


@app.route("/admin/basetimes")
@admin_required
def manage_basetimes():
    try:
        all_data = pd.read_sql(StartTime.query.statement, db.session.bind, parse_dates=['base_time'])
        dates = pd.to_datetime(all_data['base_time'])
        all_data['base_time'] = dates.dt.strftime('%Y-%m-%dT%H:%M:%S')
        return render_template("basetimes.html", rows=all_data)
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
            type(e).__name__) \
             + str(' ') + str(e)
        msg = Message('/admin/basetimes', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return render_template("basetimes.html", rows=None)


@app.route("/admin/cgflags")
@admin_required
def manage_cgflags():
    try:
        all_data = getFlagsInfo(CGFlag, CGTask, CGLabel)
        return render_template("flags.html", flags=all_data, annotation_type='CG')
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
            type(e).__name__) \
             + str(' ') + str(e)
        msg = Message('/admin/cgflags', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return render_template("flags.html", flags=[], annotation_type='CG')


@app.route("/admin/fgflags")
@admin_required
def manage_fgflags():
    try:
        all_data = getFlagsInfo(FGFlag, FGTask, FGLabel)
        return render_template("flags.html", flags=all_data, annotation_type='FG')
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
            type(e).__name__) \
             + str(' ') + str(e)
        msg = Message('/admin/fgflags', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return render_template("flags.html", flags=[], annotation_type='FG')


@app.route("/admin/unflag/<annotator_id>/<task_id>/<annotation_type>/<flagid>", methods=['GET', 'POST'])
@admin_required
def unflag(annotator_id, task_id, annotation_type, flagid):
    try:
        if annotation_type == 'CG':
            tasktable, flagtable = CGTask, CGFlag
            workallocator = cgworkallocator
        else:
            tasktable, flagtable = FGTask, FGFlag
            workallocator = fgworkallocator

        task = db.session.query(tasktable).filter(
            (tasktable.id == task_id) & (tasktable.allocated_to == annotator_id)).one()
        task.allocated_to = None

        db.session.query(flagtable).filter(flagtable.id == flagid).delete()
        # update workallocator
        db.session.commit()
        flash("Unflagged Successfully")
        return redirect(url_for("manage_cgflags")) if annotation_type == 'CG' else redirect(url_for("manage_fgflags"))
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
            type(e).__name__) \
             + str(' ') + str(e)
        msg = Message('/admin/unflag/', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        flash("Unflagged Failed!")
        return redirect(url_for("manage_cgflags")) if annotation_type == 'CG' else redirect(url_for("manage_fgflags"))


def getFlagsInfo(flagtable, tasktable, labeltable):
    # get the latest flag from each task_id and join it with tasktable to get info
    try:
        all_data = db.session.query(flagtable.id, flagtable.task_id, flagtable.description, flagtable.submit_time,
                                    tasktable.cgsegment_id,
                                    tasktable.audiofile_id, tasktable.patient_name, tasktable.allocated_to).join(
            tasktable).all()
        for flagrow in all_data:
            latest_label = db.session.query(labeltable.submit_time).join(tasktable) \
                .filter((labeltable.task_id == flagrow.task_id) & (tasktable.allocated_to == flagrow.allocated_to)) \
                .order_by(labeltable.submit_time.desc()).first()
            if latest_label:
                if latest_label.submit_time > flagrow.submit_time:
                    all_data.remove(flagrow)
        return all_data
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
            type(e).__name__) \
             + str(' ') + str(e)
        msg = Message('getFlagsInfo', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return []


@app.route('/updatebasetime', methods=['GET', 'POST'])
@admin_required
def updatebasetime():
    if request.method == 'POST':
        try:
            row = StartTime.query.get(request.form.get('id'))
            if row.annotationtype == 'cg':
                cgworkallocator.set_start_time(row.patient_name, request.form['base_time'])
            else:
                fgworkallocator.set_start_time(row.patient_name, request.form['base_time'])
            db.session.commit()
            flash("Basetime Updated Successfully")
            return redirect(url_for('manage_basetimes'))
        except Exception as e:
            db.session.rollback()
            flash("Update Basetime Failed! ", str(e))
            return redirect(url_for('manage_basetimes'))


@app.route("/admin/workprogress")
@admin_required
def view_workprogress():
    try:
        all_data = db.session.query(WorkProgress).all()
        return render_template("workprogress.html", rows=all_data)
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
            type(e).__name__) \
             + str(' ') + str(e)
        msg = Message('/admin/workprogress', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return render_template("workprogress.html", rows=[])


@app.route("/admin/fgpasshandler")
@admin_required
def view_fgpasshandler():
    try:
        all_data = db.session.query(FGPassHandler).all()
        return render_template("fgpasshandler.html", rows=all_data)
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
            type(e).__name__) \
             + str(' ') + str(e)
        msg = Message('/admin/fgpasshandler', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return render_template("fgpasshandler.html", rows=[])


@app.route("/admin/patients")
@admin_required
def view_patients():
    try:
        all_data = db.session.query(Patient).all()
        return render_template("patients.html", patients=all_data)
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
            type(e).__name__) \
             + str(' ') + str(e)
        msg = Message('/admin/patients', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return render_template("patients.html", patients=[])


# @app.route("/admin/audiofiles")
# @admin_required
# def view_audiofiles():
#     all_data = db.session.query(AudioFile).all()
#     return render_template("audiofiles.html", files=all_data)
#
# @app.route("/admin/nonsilentsegments")
# @admin_required
# def view_nonsilentsegments():
#     all_data = db.session.query(NonSilentSegment).all()
#     return render_template("nonsilentsegments.html", files=all_data)
#
# @app.route("/admin/cgsegments")
# @admin_required
# def view_cgsegments():
#     all_data = db.session.query(CGSegment).all()
#     return render_template("cgsegments.html", files=all_data)
#
# @app.route("/admin/cgtasks")
# @admin_required
# def view_cgtasks():
#     all_data = db.session.query(CGTask).all()
#     return render_template("cgtasks.html", tasks=all_data)
#
# @app.route("/admin/fgtasks")
# @admin_required
# def view_fgtasks():
#     all_data = db.session.query(FGTask).all()
#     return render_template("fgtasks.html", tasks=all_data)
#
# @app.route("/admin/cgbatches")
# @admin_required
# def view_cgbatches():
#     all_data = db.session.query(CGBatch).all()
#     return render_template("cgbatches.html", batches=all_data)
#
# @app.route("/admin/fgbatches")
# @admin_required
# def view_fgbatches():
#     all_data = db.session.query(FGBatch).all()
#     return render_template("fgbatches.html", batches=all_data)
#
@app.route("/admin/cglabels")
@admin_required
def view_cglabels():
    all_data = db.session.query(CGLabel.id, CGLabel.task_id, CGLabel.label, CGLabel.submit_time, CGLabel.annotator_id, CGTask.patient_name, CGTask.audiofile_id, CGTask.cgsegment_id).join(CGTask).all()
    return render_template("cglabels.html", labels=all_data)
#
@app.route("/admin/fglabels")
@admin_required
def view_fglabels():
    all_data = db.session.query(FGLabel.id, FGLabel.task_id, FGLabel.label, FGLabel.start, FGLabel.end, FGLabel.submit_time, FGLabel.annotator_id, FGTask.patient_name, FGTask.audiofile_id, FGTask.cgsegment_id).join(FGTask).all()
    return render_template("fglabels.html", labels=all_data)


# @app.route("/admin/view_fglabel_details")
# # @admin_required
# def view_fgfdflabels():
#     # all_data = db.session.query(FGLabel.id, FGLabel.task_id, FGLabel.label, FGLabel.start, FGLabel.end, FGTask.allocated_to, FGTask.patient_name, FGTask.audiofile_id, FGTask.cgsegment_id).join(FGTask).all()
#     # print(all_data)
#     return render_template("view_fglabel_details.html")


@app.route("/admin/playaudio")
@admin_required
def playaudio():
    cgsegment_id = request.args.get('cgsegment_id', 1)
    audiofile_id = request.args.get('audiofile_id', 1)
    patient_name = request.args.get('patient_name', 'copdpatient29')
    return render_template("playaudio.html", cgsegment_id=cgsegment_id, audiofile_id=audiofile_id,
                           patient_name=patient_name)


@app.route("/admin/validate_annotators")
@admin_required
def validate_annotators():
    user_ids = db.session.query(User.id).filter(User.role == 'annotator').filter(User.status == 'active').all()
    user_ids = [r[0] for r in user_ids]
    fg_jaccard_indexes = {}  # dictionary of dictionary of list of tuples (each list contains jaccard indexes for each batch_number
    cg_jaccard_indexes = {}  # dictionary of dictionary of list of tuples (each list contains jaccard indexes for each batch_number
    for usr in user_ids:
        fg_jaccard_indexes[usr] = {}
        cg_jaccard_indexes[usr] = {}
        # find the latest batch_number:
        # FG
        max_fg_batch_number = db.session.query(func.max(FGBatch.batch_number)).filter(
            FGBatch.annotator_id == usr).scalar()
        if max_fg_batch_number != None:
            for batch_number in range(1, max_fg_batch_number + 1):
                if batch_number in [1, 2, 3, 4]:
                    latestlabels = get_latest_labels(FGLabel, FGTask, usr, batch_number)
                    # intial tests
                    fg_jaccard_indexes[usr][batch_number] = calc_jaccard_index_initial('fg', latestlabels)
                elif batch_number % 10 == 0:  # repeated tests
                    latestlabels = get_latest_labels(FGLabel, FGTask, usr, batch_number)
                    fg_jaccard_indexes[usr][batch_number] = calc_jaccard_index_initial('fg', latestlabels[
                        latestlabels.task_id.isin(fg_test_initial)])
        # CG
        max_cg_batch_number = db.session.query(func.max(CGBatch.batch_number)).filter(
            CGBatch.annotator_id == usr).scalar()
        if max_cg_batch_number != None:
            for batch_number in range(1, max_cg_batch_number + 1):
                if batch_number in [1, 2, 3, 4]:
                    # intial tests
                    latestlabels = get_latest_labels(CGLabel, CGTask, usr, batch_number)
                    cg_jaccard_indexes[usr][batch_number] = calc_jaccard_index_initial('cg', latestlabels)
                elif batch_number % 10 == 0:  # repeated tests
                    latestlabels = get_latest_labels(CGLabel, CGTask, usr, batch_number)
                    # print(latestlabels)
                    # print("gg", latestlabels.task_id.isin(cg_test_initial))
                    # print("this", latestlabels[latestlabels.task_id.isin(cg_test_initial)])
                    cg_jaccard_indexes[usr][batch_number] = calc_jaccard_index_initial('cg', latestlabels[
                        latestlabels.task_id.isin(cg_test_initial)])
    # print(cg_jaccard_indexes)
    return render_template("validate_annotators.html", fg_jaccard_indexes=fg_jaccard_indexes,
                           cg_jaccard_indexes=cg_jaccard_indexes)


# @app.route("/admin/telemetry")
# @admin_required
# def view_telemetry():
#     all_data = db.session.query(Telemetry).all()
#     return render_template("telemetry.html", logs=all_data)
#
# @app.route("/admin/cglogtasks")
# @admin_required
# def view_cglogtasks():
#     all_data = db.session.query(CGLogTask).all()
#     return render_template("cglogtasks.html", logs=all_data)
#
# @app.route("/admin/fglogtasks")
# @admin_required
# def view_fglogtasks():
#     all_data = db.session.query(FGLogTask).all()
#     return render_template("fglogtasks.html", logs=all_data)
#
# @app.route("/admin/cglogbatches")
# @admin_required
# def view_cglogbatches():
#     all_data = db.session.query(CGLogBatch).all()
#     return render_template("cglogbatches.html", logs=all_data)
#
# @app.route("/admin/fglogbatches")
# @admin_required
# def view_fglogbatches():
#     all_data = db.session.query(FGLogBatch).all()
#     return render_template("fglogbatches.html", logs=all_data)

@app.route("/admin/useractivity")
@admin_required
def view_useractivity():
    all_data = db.session.query(UserActivity).all()
    return render_template("useractivity.html", logs=all_data)


@admin_required
@app.route('/useractivity.png')
def useractivity_figure():
    df = pd.read_sql(db.session.query(UserActivity).statement, db.session.bind)
    login_times = pd.to_datetime(df.login_time)
    logout_times = pd.to_datetime(df.logout_time)

    fig = plt.Figure(tight_layout=True, figsize=(18, 5))
    ax = fig.add_subplot(111)
    xticks = login_times.append(logout_times)

    ax.plot_date(x=login_times, y=df.user_id, marker='*', color='black', xdate=True)
    ax.plot_date(x=logout_times, y=df.user_id, marker='*', color='red', xdate=True)

    xfmt = mdates.DateFormatter('%Y-%m-%d %H:%M:%S')
    ax.xaxis.set_major_formatter(xfmt)
    ax.set_xticks(xticks)
    ax.set_xticklabels(xticks, rotation=90)

    ax.set_yticks(df.user_id)
    ax.set_yticklabels(df.user_id)

    ax.set_ylabel('annotator_id')
    ax.set_xlabel('time')

    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')
