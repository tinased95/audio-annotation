import os
import random
import sys
from audio_annotation import mail
from audio_annotation.models import User, Patient, CGTask, FGTask, WorkProgress, CGBatch, FGBatch, \
    StartTime, FGPassHandler, CGLogBatch, FGLogBatch
from sqlalchemy.sql import func
from sqlalchemy import case
from datetime import datetime
import pandas as pd
from server_statics import cgDict, fgDict, CG_BATCH_SIZE, FG_BATCH_SIZE, cg_test_initial, fg_test_initial, cg_test_batch_nums, fg_test_batch_nums
from audio_annotation.functions import next_pass, read_pass_queue
import logging
from threading import Lock
from flask_mail import Message

lock = Lock()


class WorkAllocator:
    def __init__(self, db, annotation_type):
        """
        allocations[(cgsegment_id, pass_id)] = [# allocated, #total]
        blacklist[annotator_id] = {pass_id: set of cgsegment_ids }  >>> key: annotator_id --> pass_id --> a set of segments
        Info = recordtype('Info', 'allocated total')
        :param annotation_type: cg or fg
        """

        t1 = datetime.now()
        self.db = db
        self.annotation_type = annotation_type
        print('Initializing ' + self.annotation_type)
        if annotation_type == 'cg':
            self.batchtable, self.logbatchtable, self.tasktable, self.passes = CGBatch, CGLogBatch, CGTask, cgDict
            self.batch_size = CG_BATCH_SIZE
        else:
            self.batchtable, self.logbatchtable, self.tasktable, self.passes = FGBatch, FGLogBatch, FGTask, fgDict
            self.batch_size = FG_BATCH_SIZE

        self.patient_order, self.current_patient_index = self.init_patients()
        self.allocations, self.blacklist = self.init_allocations_and_blacklists()
        # self.base_times = self.init_base_times() # no need for this

        self.logformatter = logging.Formatter('%(asctime)s - %(message)s')

        self.logprints = self.setup_logger('loginfo', 'prints.log')
        self.loginfo = self.setup_logger('loginfo', 'batch.log')
        self.logerror = self.setup_logger('logerror', 'workallocator_error.log')
        # self.checkpoint = self.setup_logger('checkpoint', self.annotation_type + 'checkpoint.log')
        t2 = datetime.now()
        print("All have been initialized in", t2 - t1)
        self.logprints.info(f'Server initialized, type={self.annotation_type}, server_initialization={t2 - t1}')

    def init_patients(self):  # tamoom
        patients = self.db.session.query(Patient.name).all()
        try:
            assert patients != None and len(patients) > 0
        except AssertionError as err:
            self.logerror.error("no patients found")
            raise err

        patients = [r[0] for r in patients]
        nextpatient = self.db.session.query(WorkProgress).filter(WorkProgress.type == self.annotation_type).first()
        if nextpatient == None:
            current_patient_index = 0
            # initialize WorkProgress table
            workp = WorkProgress(type=self.annotation_type, patient_name=patients[current_patient_index])
            self.db.session.add(workp)
            self.db.session.commit()
        else:
            if nextpatient.patient_name in patients:
                current_patient_index = patients.index(nextpatient.patient_name)
            else:
                current_patient_index = 0
                nextpatient.patient_name = patients[0]
                self.db.session.commit()
        return patients, current_patient_index

    def init_base_times(self):
        base_times = {}
        allrows = self.db.session.query(StartTime.patient_name, StartTime.base_time).all()
        for patient_basetime in allrows:
            base_times[patient_basetime[0]] = patient_basetime[1]
        return base_times

    def set_start_time(self, patient_name, base_time):
        # self.base_times[patient_name] = base_time
        # update db
        self.db.session.query(StartTime).filter(
            (StartTime.patient_name == patient_name) & (StartTime.annotationtype == self.annotation_type)
        ).update({
            StartTime.base_time: base_time
        }, synchronize_session=False)
        self.db.session.commit()

    def init_allocations_and_blacklists(self):  # tamoom
        allocations = {}
        blacklist = {}
        # get segment_id, pass_id, allocated, total
        id_pass_finished_total = pd.read_sql(
            self.db.session.query(self.tasktable.cgsegment_id, self.tasktable.pass_id,
                                  func.count(case([(self.tasktable.allocated_to != None, 1)])),
                                  func.count(self.tasktable.cgsegment_id))
                .group_by(self.tasktable.cgsegment_id, self.tasktable.pass_id).statement,
            self.db.session.bind)
        for row in id_pass_finished_total.itertuples(index=False):
            try:
                assert row.count_1 <= row.count_2  # finished <= total
            except AssertionError as err:
                msg = Message('/workallocator/init_allocations_and_blacklists', sender=os.environ['EMAIL_SENDER'],
                              recipients=[os.environ['EMAIL_RECEIVER']],
                              body=f'num_finished is greater than total!')
                mail.send(msg)
                self.logerror.error("num_finished is greater than total!")
                raise err

            if row.count_1 != row.count_2:  # if #finished != total
                # allocations[(cgsegment_id, pass_id)] = [#allocated, #total]
                allocations[(row.cgsegment_id, row.pass_id)] = [row.count_1,
                                                                row.count_2]  # Info(row.count_1, row.count_2)

        user_ids = self.db.session.query(User.id).filter(User.role == 'annotator').filter(User.status == 'active').all()
        # check if None
        user_ids = [r[0] for r in user_ids]

        for usr in user_ids:
            blacklist[usr] = {}
            for p in self.passes:
                blacklist[usr][p] = set()
            allcgsegment_passids = self.db.session.query(self.tasktable.cgsegment_id, self.tasktable.pass_id).filter(
                self.tasktable.allocated_to == usr).all()
            for cgsegment_passid in allcgsegment_passids:
                if cgsegment_passid in allocations and allocations[cgsegment_passid][0] != 0:  # if it is incomplete:
                    blacklist[usr][cgsegment_passid[1]].add(cgsegment_passid[0])
        return allocations, blacklist

    def add_to_allocations(self, cgsegment_id, pass_id, n_total):  # no usage
        self.allocations[(cgsegment_id, pass_id)] = [0, n_total]

    def remove_from_allocations(self, cgsegment_id, pass_id):
        self.allocations.pop((cgsegment_id, pass_id))

    def add_to_blacklist(self, usr):
        self.blacklist[usr] = {}
        for p in self.passes:
            self.blacklist[usr][p] = set()

    def create_batch(self, annotator_id, batch_size=None):  # CGBatch, CGTask, cgworkallocator
        with lock:
            try:
                # check if annotator_id is in annotators
                check_annotatorid = self.db.session.query(User.id).filter(User.id == annotator_id).one()
                queries_info = []
                t1 = datetime.now()
                if batch_size is None:
                    batch_size = self.batch_size

                # find previous batch number by this annotator
                prev_batch_number = self.db.session.query(func.max(self.batchtable.batch_number)).filter(
                    self.batchtable.annotator_id == annotator_id).scalar()

                if prev_batch_number is not None:  # this annotator has annotated at least one batch
                    new_batch_number = prev_batch_number + 1
                else:  # first time creating a batch for this annotator
                    new_batch_number = 1

                random_position_in_batch = -1
                random_task_id = -1
                if self.annotation_type == 'cg':
                    chosen_pass_id = '0'
                    # initial batches
                    if new_batch_number in range(1, cg_test_batch_nums+1): 
                        ids = cg_test_initial[(new_batch_number - 1) * batch_size: new_batch_number * batch_size] # could be [1..10], [11..20], [21..30], [31..40]
                    # one test every 10 batches
                    elif new_batch_number % 10 == 0 and cg_test_batch_nums!= 0:
                        ids = self.retrieve_ids(batch_size - 1, chosen_pass_id, annotator_id, queries_info)
                        random_position_in_batch = random.choice(range(0, len(ids)))
                        random_task_id = random.choice(cg_test_initial[:20])
                        # choose a random index from ids and insert the segment with the random task_id from [0, 10]
                        # print('random_position_in_batch', random_position_in_batch, 'random_task_id', random_task_id)
                        self.logprints.info(
                            f'Testing batch, type={self.annotation_type}, position={random_position_in_batch}, task_id={random_task_id}')
                        ids.insert(random_position_in_batch, random_task_id)

                    # normal batch
                    else:
                        ids = self.retrieve_ids(batch_size, chosen_pass_id, annotator_id, queries_info)
                else: # if fg
                    ids = []
                    count = 0  # count chosen passes
                    # initial batches
                    if new_batch_number in range(1, fg_test_batch_nums+1):  # initial batches
                        chosen_pass_id = '0'
                        ids = fg_test_initial[(new_batch_number - 1) * batch_size: new_batch_number * batch_size] # could be [1..10], [11..20], [21..30], [31..40]
                        # one test every 10 batches
                    elif new_batch_number % 10 == 0 and fg_test_batch_nums!= 0:
                        chosen_pass_id = '0'
                        ids = self.retrieve_ids(batch_size - 1, chosen_pass_id, annotator_id, queries_info)
                        if len(ids) != 0:
                            random_position_in_batch = random.choice(range(0, len(ids)))
                            random_task_id = random.choice(fg_test_initial[:20])
                            # choose a random index from ids and insert the segment with the random task_id from [0, 10]
                            # print('random_position_in_batch', random_position_in_batch, 'random_task_id', random_task_id)
                            self.logprints.info(
                                f'Testing batch, type={self.annotation_type}, position={random_position_in_batch}, task_id={random_task_id}')
                            ids.insert(random_position_in_batch, random_task_id)

                    else:
                        # the loop to choose all the ids
                        while not ids and count <= len(fgDict):
                            skip_pass = False if count == 0 else True  # only the first time skip_pass is False
                            chosen_pass_id = self.decide_pass_id(annotator_id, skip_pass=skip_pass)
                            # print("chosen_pass_id:", chosen_pass_id)
                            ids = self.retrieve_ids(batch_size, chosen_pass_id, annotator_id, queries_info)
                            count += 1

                self.insert_batch(ids, new_batch_number, annotator_id)
                self.insert_logbatch(annotator_id, new_batch_number)
                if new_batch_number not in [1, 2, 3, 4]:
                    self.update_tasks(ids, annotator_id, random_task_id)
                    self.update_next_patient_in_work_progress_table()

                self.db.session.commit()
                t2 = datetime.now()
                self.loginfo.info(
                    f'type={self.annotation_type}, annotator_id={annotator_id}, len_blacklist={len(self.blacklist[annotator_id][chosen_pass_id])}, pass_id={chosen_pass_id}, batch_num={new_batch_number}, time={t2 - t1}, ids={ids}, info={queries_info}')

                batch = self.db.session.query(self.batchtable).filter(
                    self.batchtable.annotator_id == annotator_id).filter(
                    self.batchtable.is_done == False).order_by(self.batchtable.num_in_batch.asc()).first()
                return batch  #### change this to return ids for performance analysis
            except Exception as e:
                self.db.session.rollback()
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                er = str(exc_type) + str(' ') + str(fname) + str(' ') + str(exc_tb.tb_lineno) + str(' ') + str(
                    type(e).__name__) \
                     + str(' ') + str(e) + ' userid: ' + str(annotator_id)

                msg = Message('/workallocator', sender=os.environ['EMAIL_SENDER'],
                              recipients=[os.environ['EMAIL_RECEIVER']],
                              body=er)
                mail.send(msg)
                self.logerror.error(f'Error in creating the {self.annotation_type} batch for annotator {annotator_id}, {er}')
                # raise

    def update_tasks(self, ids, annotator_id, random_task_id):
        # print("update tasks")
        ts = datetime.now()
        for i in ids:
            if random_task_id != i:  # don't update task for the 'test' task_id
                # print("updating task")
                task = self.db.session.query(self.tasktable).filter(self.tasktable.id == i).first()
                try:
                    assert task.allocated_to == None or task.allocated_to == annotator_id
                    task.allocated_to = annotator_id
                    self.db.session.add(task)
                except AssertionError as err:
                    msg = Message('/workallocator/update_tasks', sender=os.environ['EMAIL_SENDER'],
                                  recipients=[os.environ['EMAIL_RECEIVER']],
                                  body=f'Error in updating Task table, its already allocated! annotator: {annotator_id}')
                    mail.send(msg)
                    self.logerror.error("Error in updating Task table, it's already allocated!")
                    raise err
            else:
                "This is a test task!"

    def insert_batch(self, ids, batch_number, annotator_id):
        num = 1
        batch_size = len(ids)
        for taskid in ids:
            local_batch = self.batchtable(task_id=taskid, annotator_id=annotator_id,
                                          batch_number=batch_number, num_in_batch=num, batch_size=batch_size)
            num += 1
            self.db.session.add(local_batch)

    def insert_logbatch(self, annotator_id, batch_number):
        logbatchstart = self.db.session.query(self.logbatchtable).filter(
            (self.logbatchtable.annotator_id == annotator_id) & (
                    self.logbatchtable.batch_number == batch_number)).first()

        if not logbatchstart:
            logbatch = self.logbatchtable(annotator_id=annotator_id, batch_number=batch_number,
                                          batch_start_time=datetime.now())
            self.db.session.add(logbatch)

    def query_patient_segments(self, batch_size, patient_name, start_time, blacklist, source_segment_list, pass_id, ids):
        # print("query_patient_segments", patient_name, pass_id)

        t1 = datetime.now()
        if pass_id == '3':
            sorted = pd.read_sql(
                self.db.session.query(self.tasktable.id, self.tasktable.start_time, self.tasktable.cgsegment_id,
                                      self.tasktable.pass_id, self.tasktable.audiofile_id) \
                    .filter(self.tasktable.allocated_to == None, self.tasktable.patient_name == patient_name,
                            self.tasktable.pass_id == pass_id) \
                    .filter(self.tasktable.cgsegment_id.in_(source_segment_list)) \
                    .filter(~self.tasktable.cgsegment_id.in_(blacklist)) \
                    .filter(~self.tasktable.id.in_(ids)) \
                    .filter(self.tasktable.start_time > start_time) \
                    .distinct(self.tasktable.start_time, self.tasktable.cgsegment_id, self.tasktable.pass_id) \
                    .order_by(self.tasktable.start_time, self.tasktable.cgsegment_id) \
                    .limit(batch_size).statement, self.db.session.bind)  # *FG_NUM_REPT
           
        else:
            sorted = pd.read_sql(
                self.db.session.query(self.tasktable.id, self.tasktable.start_time, self.tasktable.cgsegment_id,
                                      self.tasktable.pass_id, self.tasktable.audiofile_id) \
                    .filter(self.tasktable.allocated_to == None, self.tasktable.patient_name == patient_name,
                            self.tasktable.pass_id == pass_id) \
                    .filter(~self.tasktable.cgsegment_id.in_(blacklist)) \
                    .filter(~self.tasktable.id.in_(ids)) \
                    .filter(self.tasktable.start_time > start_time) \
                    .distinct(self.tasktable.start_time, self.tasktable.cgsegment_id, self.tasktable.pass_id) \
                    .order_by(self.tasktable.start_time, self.tasktable.cgsegment_id) \
                    .limit(batch_size).statement, self.db.session.bind)  # *FG_NUM_REPT

        t2 = datetime.now()

        # get only segments of one audiofile
        df_final = sorted[sorted.audiofile_id.diff().ne(0).cumsum().eq(1)]
        # print("done query_patient_segments in", t2 - t1)
        print(df_final)
        return df_final, (patient_name, len(df_final), str(t2 - t1))

    def decide_pass_id(self, annotator_id, skip_pass=False):  # if skip_pass == False, go to the next pass
        fgpass = self.db.session.query(FGPassHandler).filter(FGPassHandler.annotator_id == annotator_id).one()
        if skip_pass is False:
            # go to the next
            fgpassqueue = read_pass_queue()
            desired_pass_count = fgpassqueue[fgpass.pass_number]
            if desired_pass_count <= fgpass.count:  # go to a new pass
                # print("go to a new pass")
                chosen_pass_id = next_pass(fgpass.pass_number)
                if chosen_pass_id is None:  # it means that all the pass ids are 0
                    return None
                fgpass.pass_number = chosen_pass_id
                fgpass.count = 1
                # self.db.session.commit()
                return chosen_pass_id
            else:  # increase count and return the pass_id
                # print("increase current pass count")
                fgpass.count += 1
                # self.db.session.commit()
                return fgpass.pass_number

        else:
            # print("skip pass is True so retireve next pass")
            chosen_pass_id = next_pass(fgpass.pass_number)
            # update handler
            fgpass.pass_number = chosen_pass_id
            fgpass.count = 1
            # self.db.session.commit()
            return chosen_pass_id

    def get_next_patient(self):
        # get the next patient from the list (circular)
        if len(self.patient_order) - 1 == self.current_patient_index:  # the last index
            self.current_patient_index = 0
        else:
            self.current_patient_index += 1

    def update_next_patient_in_work_progress_table(self):
        # update_patient_cursor
        work = self.db.session.query(WorkProgress).filter(
            WorkProgress.type == self.annotation_type).one_or_none()  # a two row table
        if not work:
            work = WorkProgress(type=self.annotation_type, patient_name=self.current_patient_index)
            self.db.session.add(work)
        else:
            work.patient_name = self.patient_order[self.current_patient_index]

    def retrieve_ids(self, batch_size, chosen_pass_id, annotator_id, queries_info):
        ts = datetime.now()
        # print("retrieve_ids")
        source_segment_list = set()
        if chosen_pass_id == '3':
            segments = self.db.session.query(self.tasktable.cgsegment_id) \
                .group_by(self.tasktable.cgsegment_id) \
                .having(
                (func.count(case([(((self.tasktable.pass_id == '0') & (self.tasktable.allocated_to == None)), self.tasktable.id)])) == 0)
                &
                (func.count(case([(((self.tasktable.pass_id == '3') & (self.tasktable.allocated_to == None)), self.tasktable.id)])) != 0)
            ).all()
            for s in segments:
                source_segment_list.add(s[0])
        
        new_batch_size = 0  # this will be increased in the while loop
        counter = 0  # number of consecutive patients with no tasks
        ids = []  # task ids that are selected
        while new_batch_size < batch_size and counter <= len(self.patient_order):
            patient_name = self.patient_order[self.current_patient_index]
            start_time = self.db.session.query(StartTime.base_time).filter(
                (StartTime.patient_name == patient_name) & (StartTime.annotationtype == self.annotation_type)).scalar()
            patient_segments, info = self.query_patient_segments(batch_size=batch_size - new_batch_size,
                                                                 patient_name=patient_name, start_time=start_time,
                                                                 blacklist=self.blacklist[annotator_id][chosen_pass_id],
                                                                 source_segment_list=source_segment_list,
                                                                 pass_id=chosen_pass_id, ids=ids)

            print(batch_size, new_batch_size, source_segment_list)
            queries_info.append(info)
            if patient_segments.empty:
                counter += 1
            else:
                counter = 0
                for row in patient_segments.itertuples(index=False):
                    s = row.cgsegment_id
                    p = row.pass_id
                    try:
                        assert s not in self.blacklist[annotator_id][chosen_pass_id], 'segment_id' + str(s)
                    except AssertionError as err:
                        self.logerror.error(f'segment_id: {s} is already in the blacklist')
                        msg = Message('/workallocator/retrieve_ids', sender=os.environ['EMAIL_SENDER'],
                                      recipients=[os.environ['EMAIL_RECEIVER']],
                                      body=f'segment_id: {s} is already in the blacklist annotator: {annotator_id}')
                        mail.send(msg)
                        raise err

                    try:
                        assert row.id not in ids, 'row_id:' + str(row.id)
                    except AssertionError as err:
                        self.logerror.error(f'task_id: {row.id} is already in ids')
                        msg = Message('/workallocator/retrieve_ids', sender=os.environ['EMAIL_SENDER'],
                                      recipients=[os.environ['EMAIL_RECEIVER']],
                                      body=f'task_id: {row.id} is already in ids annotator: {annotator_id}')
                        mail.send(msg)
                        raise err

                    try:
                        assert p == chosen_pass_id
                    except AssertionError as err:
                        msg = Message('/workallocator/retrieve_ids', sender=os.environ['EMAIL_SENDER'],
                                      recipients=[os.environ['EMAIL_RECEIVER']],
                                      body=f' pass id should have been {chosen_pass_id} but got {p} annotator: {annotator_id}')
                        mail.send(msg)
                        self.logerror.error(f' pass id should have been {chosen_pass_id} but got {p}')
                        raise err

                    count_temp = 0
                    for usr in self.blacklist:
                        if s in self.blacklist[usr][chosen_pass_id]:
                            count_temp += 1
                    if count_temp != 0:
                        try:
                            assert count_temp == self.allocations[(s, chosen_pass_id)][0]
                        except AssertionError as err:
                            msg = Message('/workallocator/retrieve_ids', sender=os.environ['EMAIL_SENDER'],
                                          recipients=[os.environ['EMAIL_RECEIVER']],
                                          body=f' number of times {s} appears in the blacklists does not match with self.allocations annotator: {annotator_id}')
                            mail.send(msg)
                            self.logerror.error(
                                f' number of times {s} appears in the blacklists does not match with self.allocations')
                            raise err

                    if (s, p) in self.allocations:
                        # if it's the last task for this (cgsegment_id, pass_id), remove it from the blacklist (allocated + 1 == total))
                        if self.allocations[(s, p)][0] + 1 == self.allocations[(s, p)][1]:
                            popped = self.allocations.pop((s, p))
                            # print("popped: ", (s, p), popped)
                            # remove from all blacklists
                            for usr in self.blacklist:
                                if s in self.blacklist[usr][p]:
                                    self.blacklist[usr][p].remove(s)
                        else:  # if the cgsegment is going to be alllocated to the annotater_id
                            self.allocations[(s, p)][0] += 1
                            self.blacklist[annotator_id][p].add(s)
                    else:  # its a new cgsegment_id so initialize blacklist and allocations
                        self.allocations[(s, p)] = [1, 2]
                        self.blacklist[annotator_id][p].add(s)

                    ids.append(row.id)
                    new_batch_size += 1
            # update current patient
            self.get_next_patient()
        # print("done retrieve_ids", datetime.now() - ts)
        print("ids", ids)
        return ids

    def setup_logger(self, name, log_file, level=logging.INFO):
        """To setup as many loggers as you want"""
        logger = logging.getLogger(name)
        logger.setLevel(level)

        if (logger.hasHandlers()):
            logger.handlers.clear()
        handler = logging.FileHandler(log_file)
        handler.setFormatter(self.logformatter)
        logger.addHandler(handler)

        return logger
