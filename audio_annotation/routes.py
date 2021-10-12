import os
import sys

from flask import render_template, url_for, flash, redirect, request, jsonify, session

from audio_annotation.admin_pages import get_logtasks
from audio_annotation.decorators import annotator_required
from audio_annotation.models import User, UserActivity, CGLogTask, CGLogBatch, CGFlag, CGTask, CGBatch, FGLogTask, \
    FGLogBatch, FGFlag, FGTask, FGBatch, CGLabel, FGLabel
from audio_annotation import app, db, bcrypt, mail
from audio_annotation.forms import LoginForm
from flask_login import login_user, current_user, logout_user, login_required
from audio_annotation.functions import get_file, update_sessions
from audio_annotation.functions import save_telemetry
from datetime import datetime
import random, json
from flask_mail import Message
from sqlalchemy import desc
from sqlalchemy import func, and_

@app.route("/")
@app.route("/index")
@login_required
@annotator_required
def index():
    return render_template('index.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.query(User).filter(User.email==form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data) and user.status == 'active':
            try:
                login_time = datetime.now()
                record_logintime = UserActivity(user_id=user.id, login_time=login_time)
                db.session.add(record_logintime)
                # session['login_time'] = datetime.now()
                auth_session_token = random.getrandbits(128)
                auth_session_token = '%032x' % auth_session_token
                user.session_token = auth_session_token
                db.session.commit()
                login_user(user, remember=form.remember.data)
                if user.is_temp_pw:
                    return redirect(url_for('newPassword'))

                if user.role == 'admin':
                    return redirect(url_for('annotators_progress'))
                save_telemetry(annotator_id=user.id, ts=login_time, action='login')
                db.session.commit()
                next_page = request.args.get('next')
                session['pop-up-instructions'] = True
                return redirect(next_page) if next_page else redirect(url_for('index'))
            except Exception as e:
                db.session.rollback()
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
                    type(e).__name__) \
                     + str(' ') + str(e)
                msg = Message('login', sender=os.environ['EMAIL_SENDER'],
                              recipients=[os.environ['EMAIL_RECEIVER']],
                              body=er)
                mail.send(msg)
                return render_template('login.html', title='Login', form=form)
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/newPassword', methods=['GET', 'POST'])
@login_required
def newPassword():
    error = None
    if request.method == 'POST':
        pw1 = request.form['pw1']
        pw2 = request.form['pw2']

        if pw1 != pw2:
            error = "Passwords do not match"
        elif len(pw1) < 4:
            error = "Password must be at least 4 characters long"
        else:
            current_user.set_password(pw1)
            db.session.add(current_user)
            db.session.commit()
            flash('Password changed successfully! You are now able to login.', 'success')
            return redirect(url_for("logout"))

    return render_template('newPassword.html', error=error)

@app.route("/logout", methods=['GET', 'POST'])
def logout():
    try:
        action= request.args.get('action', None)
        annotation_type= request.args.get('annotation_type', None)
        logout_time = datetime.now()
        # reason = request.args.get('reason')
        # if it is not already been loged out due to new logins from other devices
        # user clicked on logout button or is being log out due to inactivity
        if current_user.is_anonymous != True:
            # if not current_user.is_admin(): # is this necessary? cause I commented it
            updaterow = db.session.query(UserActivity).filter(UserActivity.user_id==current_user.id)\
                .order_by(desc('login_time')).first()
            if updaterow is not None:
                updaterow.logout_time = logout_time
                updaterow.reason = action
            save_telemetry(annotator_id=current_user.id, ts=logout_time, action=action, annotation_type=annotation_type) # , extra_info=json.dumps({"reason":reason}
            db.session.commit()
        logout_user()
        return redirect(url_for('login'))
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
            type(e).__name__) \
             + str(' ') + str(e)
        msg = Message('/logout', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return redirect(url_for('login'))


@app.route("/getFile/", methods=["GET"])
@login_required 
def get_the_file():
    patient_name = request.args.get('patient_name')
    audiofile_id = int(request.args.get('audiofile_id'))
    cgsegment_id = int(request.args.get('cgsegment_id'))
    return get_file(patient_name, audiofile_id, cgsegment_id)


@app.route("/saveTelemetry", methods=["POST"])
@login_required 
def save_telemetry_data():
    try:
        data = request.get_json()
        action = data.pop('action') # can not be None
        annotation_type = data.pop('annotation_type', None)
        task_id = data.pop('task_id', None)
        batch_number = data.pop('batch_number', None)
        # num_in_batch = data.pop('num_in_batch', None)
        extra_info = data.pop('extra_info', None)

        update_sessions(action, annotation_type) #increment corrensponding session

        save_telemetry(annotator_id=current_user.id, ts=datetime.now(), action=action,
                       annotation_type=annotation_type, task_id=task_id, batch_number=batch_number,
                       extra_info=json.dumps(extra_info))

        db.session.commit()
        return jsonify({'msg': 'success'})
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
            type(e).__name__) \
             + str(' ') + str(e)
        msg = Message('/saveTelemetry', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return jsonify({'msg': 'failed'})

@app.route("/progress")
@login_required
def progress():
    try:
        save_telemetry(annotator_id=current_user.id, ts=datetime.now(), action='check-progress',
                       annotation_type='')
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(type(e).__name__)\
             + str(' ') + str(e) + ' userid: ' + str(current_user.id)
        msg = Message('/progress/', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)

    try:
        frequencies = {'H': 'Hour', 'T': 'Minute', 'D': 'Day'}
        ann_id = current_user.id
        freq = request.args.get('freq')
        annotationtype = request.args.get('annotationtype')

        start_date = request.args.get('start_date', None)
        end_date = request.args.get('end_date', None)

        if not start_date:
            start_date = datetime(2020, 11, 11, 1, 1, 1, 1).strftime('%Y-%m-%dT%H:%M:%S')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')


        if freq == None:
            freq = 'H'
        if annotationtype == None:
            annotationtype = 'cg'

        if annotationtype == 'cg':
            logtasktable, logbatchtable, flagtable, tasktable, batchtable, labeltable = CGLogTask, CGLogBatch, CGFlag, CGTask, CGBatch, CGLabel
        else:
            logtasktable, logbatchtable, flagtable, tasktable, batchtable, labeltable = FGLogTask, FGLogBatch, FGFlag, FGTask, FGBatch, FGLabel

        xticks, num_annotations, durations, avg_time_per_task, n_previous_clicks = get_logtasks(ann_id, freq, logtasktable, start_date, end_date)

        subq = db.session.query(
            CGFlag.task_id,
            func.max(CGFlag.submit_time).label('maxdate')
        ).group_by(CGFlag.task_id).subquery('t1')

        flag_query = db.session.query(CGFlag).join(
            subq,
            and_(
                CGFlag.task_id == subq.c.task_id,
                CGFlag.submit_time == subq.c.maxdate,
                CGFlag.annotator_id == ann_id
            )
        ).all()

        n_flagged = 0
        for k in flag_query:
            label = db.session.query(CGLabel).filter(CGLabel.task_id == k.task_id).order_by(
                CGLabel.submit_time.desc()).first()
            if label:
                if label.submit_time < k.submit_time:
                    n_flagged += 1
            else:
                n_flagged += 1

        total_num_annotations_check = db.session.query(batchtable).filter(batchtable.annotator_id == ann_id).filter(
            batchtable.is_done == True).count()
        return render_template('progress.html', firstname=current_user.firstname, lastname=current_user.lastname,
                               xticks=xticks, freq=freq,
                               annotationtype=annotationtype, start_date=start_date, end_date=end_date,
                               num_annotations=num_annotations,
                               durations=durations, frequencies=frequencies,
                               num_files_annotated=sum(num_annotations),
                               total_num_annotations_check=total_num_annotations_check,
                               avg_time_per_task=avg_time_per_task, n_previous_clicks=n_previous_clicks,
                               n_flagged=n_flagged,
                               )
    except Exception as e:
        db.session.rollback()
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
            type(e).__name__) \
             + str(' ') + str(e)
        msg = Message('/progress', sender=os.environ['EMAIL_SENDER'],
                      recipients=[os.environ['EMAIL_RECEIVER']],
                      body=er)
        mail.send(msg)
        return jsonify({'msg': 'failed'})