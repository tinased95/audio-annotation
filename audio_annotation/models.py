from datetime import datetime
from audio_annotation import db, login_manager, bcrypt
from flask_login import UserMixin
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.ext.associationproxy import association_proxy
import time

@login_manager.user_loader
def load_user(session_token):
    return User.query.filter_by(session_token=session_token).first()


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(20), nullable=False)
    lastname = db.Column(db.String(20), nullable=False) 
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    registration_date = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(20), default='active')
    role = db.Column(db.String(20), default='annotator')
    is_temp_pw = db.Column(db.Boolean, nullable=False)
    session_token = db.Column(db.String(40), index=True) 

    cgBatch = db.relationship('CGBatch', backref='annotator')
    fgBatch = db.relationship('FGBatch', backref='annotator')
    userActivity = db.relationship('UserActivity', backref='annotator')
    telemetry = db.relationship('Telemetry', backref='annotator')
    cgLogTask = db.relationship('CGLogTask', backref='annotator')
    fgLogTask = db.relationship('FGLogTask', backref='annotator')
    cgLogBatch = db.relationship('CGLogBatch', backref='annotator')
    fgLogBatch = db.relationship('FGLogBatch', backref='annotator')

    def is_admin(self):
        return self.role == "admin"

    def is_annotator(self):
        return self.role == "annotator"

    def get_id(self):
        return self.session_token

    def set_password(self, password):

        self.password = bcrypt.generate_password_hash(password).decode('utf-8')
        self.is_temp_pw = False
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        return f"User('{self.id}', '{self.firstname}', '{self.lastname}', '{self.email}', '{self.registration_date}')"


class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False)
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime)
    # cursor = db.Column(db.String(10), nullable=True)

    audiofile = db.relationship('AudioFile', backref='patient')
    
    def __repr__(self):
        return f"Patient('{self.id}', '{self.name}', '{self.status}', '{self.start_date}', '{self.end_date}')"


class AudioFile(db.Model):
    __tablename__ = 'audio_file'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(50),nullable=False)
    patient_name = db.Column(db.String(50), db.ForeignKey('patient.name'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    length = db.Column(db.Integer, nullable=False)
    sample_rate = db.Column(db.Integer, nullable=False)

    UniqueConstraint('filename', 'patient_name', name='file')

    nonSilentSegment = db.relationship('NonSilentSegment', backref='audiofile')

    def __repr__(self):
        return f"Audiofile('{self.id}', '{self.filename}', '{self.patient_name}', '{self.start_time}', '{self.length}')"


class NonSilentSegment(db.Model):
    __tablename__ = 'non_silent_segment'
    id = db.Column(db.Integer, primary_key=True)
    audiofile_id = db.Column(db.Integer, db.ForeignKey('audio_file.id'), nullable=False)
    start_time = db.Column(db.Integer, nullable=False)
    length = db.Column(db.Integer, nullable=False)

    cgsegment = db.relationship('CGSegment', backref='nonsilentsegment')

    def __repr__(self):
        return f"NonSilentSegment('{self.id}', '{self.audiofile_id}', '{self.start_time}', '{self.length}')"


class CGSegment(db.Model):
    __tablename__ = 'cg_segment'
    id = db.Column(db.Integer, primary_key=True)
    nonSilentSegment_id = db.Column(db.Integer, db.ForeignKey('non_silent_segment.id'), nullable=False)
    start_time = db.Column(db.Integer, nullable=False)
    length = db.Column(db.Integer, nullable=False)

    # fgsegment = db.relationship('FGSegment', backref='cgsegment')
    cgtask = db.relationship('CGTask', backref='cgsegment')
    fgtask = db.relationship('FGTask', backref='cgsegment')

    def __repr__(self):
        return f"CGSegment('{self.id}', '{self.nonSilentSegment_id}', '{self.start_time}', '{self.length}')"

# class FGSegment(db.Model):
#     __tablename__ = 'fg_segment'
#     id = db.Column(db.Integer, primary_key=True)
#     cgSegment_id = db.Column(db.Integer, db.ForeignKey('cg_segment.id'), nullable=False)
#     # nonSilentSegment_id = db.Column(db.Integer, db.ForeignKey('non_silent_segment.id'), nullable=False)
#     # start_time = db.Column(db.Integer, nullable=False)
#     # length = db.Column(db.Integer, nullable=False)

#     fgtask = db.relationship('FGTask', backref='fgsegment')

#     def __repr__(self):
#         return f"FGSegment('{self.id}', '{self.cgSegment_id}')" #  '{self.nonSilentSegment_id}', '{self.start_time}', '{self.length}'


class CGTask(db.Model):
    __tablename__ = 'cg_task'
    id = db.Column(db.Integer, primary_key=True)
    cgsegment_id = db.Column(db.Integer, db.ForeignKey('cg_segment.id'), nullable=False)

    # copying other tables necessary columns
    audiofile_id = db.Column(db.Integer, nullable=False)
    patient_name = db.Column(db.String(20), nullable=False)
    start_time_audiofile = db.Column(db.DateTime, nullable=False) # each audio file has a start_time (exact date)
    start_time_seg = db.Column(db.Integer, nullable=False) # this is the start time of the segment (sample rate * seconds) 
    start_time = db.Column(db.DateTime, nullable = False) # sum of audiofile start time and start of segment
    sample_rate = db.Column(db.Integer, nullable=False)

    ####
    pass_id = db.Column(db.String(10), nullable=False, default=0)
    # is_in_batch = db.Column(db.Boolean, default=False, nullable=False)
    allocated_to = db.Column(db.Integer, nullable=True)

    cgbatch = db.relationship('CGBatch', uselist=False, back_populates='cgtask') # uselist=False: indicates that each cgtask is in only one batch
    cgLabel = db.relationship('CGLabel', backref='cgtask')
    # cgLog = db.relationship('CGLog', backref='cgtask')
    cgflag = db.relationship('CGFlag', backref='cgtask')

    cgLogTask = db.relationship('CGLogTask', backref='cgtask')
  
    annotator_id = association_proxy('cgbatch', 'annotator_id') # an easier way to query the batches that have annotator_id == something

    def __repr__(self):
        return f"CGTask('{self.id}', '{self.cgsegment_id}', '{self.audiofile_id}','{self.patient_name}','{self.start_time_audiofile}','{self.start_time}','{self.start_time_seg}','{self.sample_rate}','{self.pass_id}', '{self.allocated_to}')"

    
class FGTask(db.Model):
    __tablename__ = 'fg_task'
    id = db.Column(db.Integer, primary_key=True)
    # fgsegment_id = db.Column(db.Integer, db.ForeignKey('fg_segment.id'), nullable=False)
    cgsegment_id = db.Column(db.Integer, db.ForeignKey('cg_segment.id'), nullable=False)
    
    # copying other tables necessary columns
    audiofile_id = db.Column(db.Integer, nullable=False)
    patient_name = db.Column(db.String(20), nullable=False)
    start_time_audiofile = db.Column(db.DateTime, nullable=False) # each audio file has a start_time (exact date)
    start_time_seg = db.Column(db.Integer, nullable=False) # this is the start time of the segment (sample rate * seconds) 
    start_time = db.Column(db.DateTime, nullable = False) # sum of audiofile start time and start of segment
    sample_rate = db.Column(db.Integer, nullable=False)
    
    pass_id = db.Column(db.String(10), nullable=False)
    # is_in_batch = db.Column(db.Boolean, default=False, nullable=False)
    allocated_to = db.Column(db.Integer, nullable=True)

    fgbatch = db.relationship('FGBatch', uselist=False, back_populates='fgtask')
    fgLabel = db.relationship('FGLabel', backref='fgtask')
    # fgLog = db.relationship('FGLog', backref='fgtask')
    fgflag = db.relationship('FGFlag', backref='fgtask')

    fgLogTask = db.relationship('FGLogTask', backref='fgtask')

    annotator_id = association_proxy('fgbatch', 'annotator_id') # an easier way to query the batches that have annotator_id == something

    def __repr__(self):
        return f"FGTask('{self.id}', '{self.cgsegment_id}', '{self.audiofile_id}','{self.patient_name}','{self.start_time_audiofile}','{self.start_time}','{self.start_time_seg}','{self.sample_rate}','{self.pass_id}', '{self.allocated_to}')"


class CGBatch(db.Model):
    __tablename__ = 'cg_batch'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('cg_task.id'))
    annotator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # patient_name = db.Column(db.String(20))
    batch_number = db.Column(db.Integer, nullable=False)
    num_in_batch = db.Column(db.Integer, nullable=False)
    batch_size = db.Column(db.Integer, nullable=False)
    is_done = db.Column(db.Boolean, default=False, nullable=False)

    # cgLogBatch = db.relationship('CGLogBatch', backref='cgbatch')

    cgtask = db.relationship("CGTask", back_populates="cgbatch")# one to one relationship

    def __repr__(self):
        return f"CGBatch('{self.id}', '{self.task_id}', '{self.annotator_id}', '{self.batch_number}', '{self.num_in_batch}', '{self.batch_size}', '{self.is_done}')"


class FGBatch(db.Model):
    __tablename__ = 'fg_batch'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('fg_task.id'))
    annotator_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    # patient_name = db.Column(db.String(20))
    batch_number = db.Column(db.Integer, nullable=False)
    num_in_batch = db.Column(db.Integer, nullable=False)
    batch_size = db.Column(db.Integer, nullable=False)
    is_done = db.Column(db.Boolean, default=False,  nullable=False)

    # fgLogBatch = db.relationship('FGLogBatch', backref='fgbatch')

    fgtask = db.relationship("FGTask", back_populates="fgbatch")# one to one relationship

    def __repr__(self):
        return f"FGBatch('{self.id}', '{self.task_id}', '{self.annotator_id}', '{self.batch_number}', '{self.num_in_batch}', '{self.batch_size}', '{self.is_done}')"


class CGLabel(db.Model):
    __tablename__ = 'cg_label'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('cg_task.id'), nullable=False)
    label = db.Column(db.Boolean)
    submit_time = db.Column(db.DateTime, default=datetime.now)
    annotator_id = db.Column(db.Integer, nullable=False)
    batch_number = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"CGLabel('{self.id}', '{self.task_id}', '{self.label}', '{self.submit_time}', '{self.annotator_id}', '{self.batch_number}')"


class FGLabel(db.Model):
    __tablename__ = 'fg_label'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('fg_task.id'), nullable=False)
    label = db.Column(db.String(20))
    start = db.Column(db.Integer, nullable=False)
    end = db.Column(db.Integer, nullable=False)
    submit_time = db.Column(db.DateTime, default=datetime.now)
    annotator_id = db.Column(db.Integer, nullable=False)
    batch_number = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"FGLabel('{self.id}', '{self.task_id}', '{self.label}', '{self.start}', '{self.end}', '{self.submit_time}, '{self.annotator_id}', '{self.batch_number}')"


class CGFlag(db.Model):
    __tablename__ = 'cg_flag'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('cg_task.id'), nullable=False)
    description = db.Column(db.String(1000), nullable=False)
    submit_time = db.Column(db.DateTime, default=datetime.now)
    annotator_id = db.Column(db.Integer)
    batch_number = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"CGFlag('{self.id}', '{self.task_id}', '{self.description}', '{self.submit_time}', '{self.annotator_id}', '{self.batch_number}')"


class FGFlag(db.Model):
    __tablename__ = 'fg_flag'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('fg_task.id'), nullable=False)
    description = db.Column(db.String(1000), nullable=False)
    submit_time = db.Column(db.DateTime, default=datetime.now)
    annotator_id = db.Column(db.Integer)
    batch_number = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"FGFlag('{self.id}', '{self.task_id}', '{self.description}', '{self.submit_time}',  '{self.annotator_id}', '{self.batch_number}')"


class FGPassHandler(db.Model):
    __tablename__ = 'fg_pass_handler'
    id = db.Column(db.Integer, primary_key=True)
    annotator_id = db.Column(db.Integer, nullable=False)
    pass_number = db.Column(db.String(5), nullable=False)
    count = db.Column(db.Integer, nullable=False)


class WorkProgress(db.Model):
    __tablename__ = 'work_progress'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(5), nullable=False)
    patient_name = db.Column(db.String(30), nullable=False)
    # pass_id = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f"WorkProgress('{self.id}', '{self.type}', '{self.patient_name}')"


class UserActivity(db.Model):
    __tablename__ = 'user_activity'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    login_time = db.Column(db.DateTime, nullable=False)
    logout_time = db.Column(db.DateTime, nullable=True)
    reason = db.Column(db.String(20))

    def __repr__(self):
        return f"UserActivity('{self.id}', '{self.user_id}', '{self.login_time}', '{self.logout_time}')"


class Telemetry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    annotator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ts = db.Column(db.DateTime, default=datetime.now)
    action = db.Column(db.String(50), nullable=True)
    annotation_type = db.Column(db.String(10), nullable=True)
    task_id = db.Column(db.Integer, nullable=True)
    batch_number = db.Column(db.Integer, nullable=True)
    extra_info = db.Column(db.String(120), nullable=True)

    def __repr__(self):
        return f"Telemetry('{self.id}', '{self.annotator_id}','{self.annotation_type}','{self.task_id}','{self.batch_number}', '{self.ts}', '{self.action}', '{self.extra_info}')"


class CGLogTask(db.Model):
    __tablename__ = 'cg_log_task'
    id = db.Column(db.Integer, primary_key=True)
    annotator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('cg_task.id'), nullable=False)
    batch_number = db.Column(db.Integer, nullable=False)
    task_start_time = db.Column(db.DateTime, default=datetime.now)
    task_end_time = db.Column(db.DateTime, nullable=False)
    num_replay_server = db.Column(db.Integer) #, nullable=False
    num_replay_frontend = db.Column(db.Integer)
    action = db.Column(db.String(20)) # either submit or view

    def __repr__(self):
        return f"CGLogTask('{self.id}', '{self.annotator_id}', '{self.task_id}','{self.batch_number}', '{self.task_start_time}', '{self.task_end_time}', '{self.num_replay_server}', '{self.num_replay_frontend}', '{self.action}')"


class CGLogBatch(db.Model):
    __tablename__ = 'cg_log_batch'
    id = db.Column(db.Integer, primary_key=True)
    annotator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    batch_number = db.Column(db.Integer, nullable=False)
    batch_start_time = db.Column(db.DateTime, nullable=False)
    batch_end_time = db.Column(db.DateTime)
    num_previous_click = db.Column(db.Integer, default=0)
    num_flagged = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"CGLogBatch('{self.id}', '{self.annotator_id}', '{self.batch_number}', '{self.batch_start_time}', '{self.batch_end_time}', '{self.num_previous_click}', '{self.num_flagged}')"


class FGLogTask(db.Model):
    __tablename__ = 'fg_log_task'
    id = db.Column(db.Integer, primary_key=True)
    annotator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_id = db.Column(db.Integer, db.ForeignKey('fg_task.id'), nullable=False)
    batch_number = db.Column(db.Integer, nullable=False)
    task_start_time = db.Column(db.DateTime, default=datetime.now)
    task_end_time = db.Column(db.DateTime, nullable=False)
    num_play = db.Column(db.Integer, nullable=False)
    num_pause = db.Column(db.Integer, nullable=False)
    num_create = db.Column(db.Integer, nullable=False)
    num_move = db.Column(db.Integer, nullable=False)
    num_resize = db.Column(db.Integer, nullable=False)
    num_delete = db.Column(db.Integer, nullable=False)
    num_play_region = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(20)) # either submit or view
    # ... it can be more

    def __repr__(self):
        return f"FGLogTask('{self.id}', '{self.annotator_id}', '{self.task_id}','{self.batch_number}', '{self.task_start_time}', '{self.task_end_time}', '{self.num_play}', '{self.num_pause}','{self.num_create}', '{self.num_move}', '{self.num_resize}', '{self.num_delete}', '{self.num_play_region}', '{self.action}')"


class FGLogBatch(db.Model):
    __tablename__ = 'fg_log_batch'
    id = db.Column(db.Integer, primary_key=True)
    annotator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    batch_number = db.Column(db.Integer, nullable=False)
    batch_start_time = db.Column(db.DateTime, nullable=False)
    batch_end_time = db.Column(db.DateTime)
    num_previous_click = db.Column(db.Integer, default=0)
    num_flagged = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"FGLogBatch('{self.id}', '{self.annotator_id}', '{self.batch_number}', '{self.batch_start_time}', '{self.batch_end_time}', '{self.num_previous_click}', '{self.num_flagged}')"


class StartTime(db.Model):
    __tablename__ = 'start_time'
    id = db.Column(db.Integer, primary_key=True)
    annotationtype = db.Column(db.String(20)) # cg or fg
    patient_name = db.Column(db.String(100))
    base_time = db.Column(db.DateTime)

    def __repr__(self):
        return f"StartTime('{self.id}','{self.annotationtype}','{self.patient_name}','{self.base_time}')"

def rerun():
    print("rerun:")
    db.drop_all()
    print("dropped")
    db.create_all()
    print("created")


def add_patients():
    patient1 = Patient(name='copd20', status='active', start_date=datetime(2015, 6, 5, 8, 10, 10, 10), end_date=datetime(2016, 10, 2, 10, 1, 20, 40))
    patient2 = Patient(name='copd21', status='active', start_date=datetime(2019, 1, 1, 3, 0, 20, 4), end_date=datetime(2019, 2, 2, 10, 1, 20, 20))
    patient3 = Patient(name='copd23', status='active', start_date=datetime(2014, 2, 5, 3, 5, 11, 12), end_date=datetime(2017, 8, 1, 11, 2, 30, 45))
    
    db.session.add(patient1)
    db.session.add(patient2)
    db.session.add(patient3)

    db.session.commit()