from audio_annotation import db, bcrypt
import contextlib
import wave
from scipy.io import wavfile
from scipy import signal

import numpy as np
from matplotlib import pyplot as plt
import pandas as pd
from datetime import datetime, timedelta

import os
import glob
from itertools import islice, cycle

from audio_annotation.models import AudioFile, NonSilentSegment, CGSegment, CGTask, Patient, User
from audio_annotation.config import WORK_PATH, SEGMENT_FILES_DIRECTORY, ORIGINAL_FILES_DIRECTORY
from pathlib import Path
from server_statics import CG_NUM_REPT
import copy
import tqdm
from sqlalchemy.sql import func

# format of audio paths should be like this: .../copdn/... .wav

"""
Inputs: WORK_PATH, SEGMENT_FILES_DIRECTORY, ORIGINAL_FILES_DIRECTORY

Relative or absolute path should be configured in config.py

Pass in the directory containing all patient folders. (WORK_PATH + ORIGINAL_FILES_DIRECTORY)
pass in the directory for saving all segments. (WORK_PATH + SEGMENT_FILES_DIRECTORY)
OR
Pass in the patient_name and filename.wav to the run_silent_remover() for new files 

By running load_data(), the algorithm get files from each patient folder, calls silent remover on each file,
save the results in nonsilentsegment, cgsegment, cgtask. Also creates the actual segment files in the
SEGMENT_FILES_DIRECTORY

"""


def _read_wave(path, expected_sample_rate=None):
    if not os.path.isfile(path):
        raise ValueError("File does not exist: %s" % path)

    with contextlib.closing(wave.open(path, 'rb')) as wf:
        num_channels = wf.getnchannels()

        if num_channels != 1:
            raise ValueError("Wrong number of channels (%i) for %s" % (num_channels, path))

        sample_width = wf.getsampwidth()

        if sample_width != 2:
            raise ValueError("Wrong sample width (%i) for %s" % (sample_width, path))

        sample_rate = wf.getframerate()

        if sample_rate not in (8000, 16000, 32000):
            raise ValueError("Unsupported sample rate (%i) for %s" % (sample_rate, path))

        if expected_sample_rate is not None:
            if sample_rate != expected_sample_rate:
                raise ValueError("Sample rate (%i) for %s does not match expected rate of %i" % (
                    sample_rate, path, expected_sample_rate))

        pcm_data = wf.readframes(wf.getnframes())
        return pcm_data, sample_rate


def read_wave(path, expected_sample_rate=None):
    data, sample_rate = _read_wave(path, expected_sample_rate)
    return np.frombuffer(data, np.int16), sample_rate


def addAudioFile(filename, patient_name, length, sample_rate, start_time):
    audioFile = AudioFile(filename=filename, patient_name=patient_name, start_time=start_time, length=length,
                          sample_rate=sample_rate)
    db.session.add(audioFile)
    db.session.flush()
    db.session.commit()
    return audioFile.id

def get_noisy_segments(audio, sample_rate, threshold, overlap_s, plot=False, expected_sample_rate=None):
    # audio, sample_rate = read_wave(wav_file)

    if expected_sample_rate is not None and sample_rate != expected_sample_rate:
        raise ValueError("Wrong sample rate")

    overlap = sample_rate * overlap_s

    mask = get_noise_mask(audio, sample_rate, overlap=overlap, threshold=threshold, plot=plot)

    if len(mask) == 0:
        return [], sample_rate, len(audio)

    segs = deserialize_segs(mask)

    return segs


def smooth_segments(segs, sr, total_len, min_seg_len=None, min_non_seg_len=None, plot=False):
    new_segs = copy.deepcopy(segs)

    # Expand segments shorter than min_seg_len
    if min_seg_len is not None:
        min_seg_len_samples = min_seg_len * sr
        for seg in new_segs:
            seg_len = seg["end"] - seg["start"]
            if seg_len < min_seg_len_samples:
                diff = min_seg_len_samples - seg_len
                pad = int(diff / 2.0)
                seg["start"] = max(0, int(seg["start"] - pad))
                seg["end"] = min(total_len, int(seg["end"] + pad))

    if min_non_seg_len is not None:
        short_non_segs_removed = []

        min_non_seg_len_samples = min_non_seg_len * sr

        prev_seg = {"start": 0, "end": 0}
        for curr_seg in new_segs:
            if curr_seg["start"] - prev_seg["end"] < min_non_seg_len_samples:
                short_non_segs_removed.append({"start": prev_seg["start"], "end": curr_seg["end"]})
            else:
                short_non_segs_removed.append(curr_seg)

            prev_seg = curr_seg

        new_segs = short_non_segs_removed

    if plot:
        fig = plt.figure()
        ax = fig.add_subplot(211)
        ax.plot(serialize_segs(segs, total_len))
        ax = fig.add_subplot(212)
        ax.plot(serialize_segs(new_segs, total_len))
        plt.show()

    if min_seg_len is None and min_non_seg_len is None:
        return segs

    new_segs = deserialize_segs(serialize_segs(new_segs, total_len))

    return new_segs


def get_noise_mask(data, sample_rate, threshold, overlap=None, plot=False):
    # Apply A-weighting
    b, a = a_weighting(sample_rate)
    a_weighted_data = signal.lfilter(b, a, data)

    # Square the A-weighted data to get the signal energy
    squared_a_weighted = np.square(a_weighted_data)

    # Apply a low-pass filter
    h = signal.firwin(numtaps=10, cutoff=40, nyq=sample_rate / 2)
    lpf = signal.lfilter(h, 1.0, squared_a_weighted)

    # lpf = butter_lpf(squared_a_weighted, 10, sample_rate)

    if overlap is None:
        overlap = sample_rate * 0.5

    # Apply an average
    # averaged_lpf = overlapping_avg(lpf, overlap)
    averaged_lpf = moving_average(lpf, int(overlap))

    # Threshold the averaged data
    mask = np.copy(averaged_lpf)

    mask[mask < threshold] = 0
    mask[mask > threshold] = 1

    if plot:
        output = np.multiply(data, mask)
        graph([([data], "raw"),
               ([a_weighted_data], "A-Weight"),
               ([squared_a_weighted], "A-Weight^2"),
               ([lpf], "lpf"),
               # ([lpf1], "lpf - butterworth(10hz)"),
               ([averaged_lpf, np.full_like(averaged_lpf, threshold)], "lpf Avg",),
               ([mask], "mask"),
               ([output], "Output")]
              )

    return mask


def a_weighting(fs):
    """Design of an A-weighting filter.
    b, a = A_weighting(fs) designs a digital A-weighting filter for
    sampling frequency `fs`. Usage: y = scipy.signal.lfilter(b, a, x).
    Warning: `fs` should normally be higher than 20 kHz. For example,
    fs = 48000 yields a class 1-compliant filter.
    References:
       [1] IEC/CD 1672: Electroacoustics-Sound Level Meters, Nov. 1996.
    """
    # Definition of analog A-weighting filter according to IEC/CD 1672.
    f1 = 20.598997
    f2 = 107.65265
    f3 = 737.86223
    f4 = 12194.217
    a1000 = 1.9997

    nums = [(2 * np.pi * f4) ** 2 * (10 ** (a1000 / 20)), 0, 0, 0, 0]
    dens = np.polymul([1, 4 * np.pi * f4, (2 * np.pi * f4) ** 2],
                      [1, 4 * np.pi * f1, (2 * np.pi * f1) ** 2])
    dens = np.polymul(np.polymul(dens, [1, 2 * np.pi * f3]),
                      [1, 2 * np.pi * f2])

    # Use the bilinear transformation to get the digital filter.
    # (Octave, MATLAB, and PyLab disagree about Fs vs 1/Fs)
    return signal.bilinear(nums, dens, fs)


def moving_average(x, N=3):
    # ret = np.cumsum(x, dtype=float)
    # ret[N:] = ret[N:] - ret[:-N]
    # ret = ret[N - 1:] / N
    # hann = signal.hann(N)
    # ret = signal.convolve(x, hann, mode="same")
    # print(x.shape, pd.DataFrame(x).shape)
    ret = pd.Series(x).rolling(N, min_periods=1).mean()
    # ret = pd.rolling(x, N, min_periods=1).mean()
    return ret


def deserialize_segs(mask):
    segs = []
    consecutive_region = np.hstack((0, np.where(np.diff(mask) != 0)[0] + 1, len(mask)))

    for i in range(1, len(consecutive_region)):
        start = consecutive_region[i - 1]
        end = consecutive_region[i]

        # assert mask[start] == mask[end-1]
        if mask[start] == 1:
            segs.append({"start": start, "end": end})

    return segs


def graph(data):
    g = 1

    fig = plt.figure()

    for series, title in data:
        ax = fig.add_subplot(len(data), 1, g, title=title)
        for s in series:
            ax.plot(s)

        g += 1

    plt.show()


def serialize_segs(segs, alen):
    y = np.zeros(alen)
    for seg in segs:
        y[seg["start"]:seg["end"]] = 1

    return y


def convert_to_seconds(segs, sample_rate):
    localsegs = copy.deepcopy(segs)
    for seg in localsegs:
        seg['start'] = seg['start'] / sample_rate
        seg['end'] = seg['end'] / sample_rate
    return localsegs


def create_cgsegment_cgtask_file(audiofile_id, patient_name, audio_filename, nonsilentsegment_id, start, length,
                                 sample_rate, start_time_audiofile):
    cgsegment = CGSegment(nonSilentSegment_id=nonsilentsegment_id, start_time=start, length=length)
    db.session.add(cgsegment)
    db.session.flush()
    for i in range(CG_NUM_REPT):
        cgtask = CGTask(cgsegment_id=cgsegment.id, audiofile_id=audiofile_id, patient_name=patient_name,
                        start_time_audiofile=start_time_audiofile, start_time_seg=start,
                        start_time=(start_time_audiofile + timedelta(seconds=start / sample_rate)),
                        sample_rate=sample_rate)
        db.session.add(cgtask)
    make_file(audiofile_id, patient_name, audio_filename, start, length, cgsegment.id)


def create_segments(segs, audiofile_id, start_time_audiofile, patient_name, audio_filename, sr, min_len, max_len,
                    ideal):  # it prefers 5 over 15
    min_len, max_len, ideal = min_len * sr, max_len * sr, ideal * sr
    for seg in segs:
        length = seg['end'] - seg['start']
        # add seg to nonsilentseg
        nonSilentSegment = NonSilentSegment(audiofile_id=audiofile_id, start_time=int(seg['start']), length=int(length))
        db.session.add(nonSilentSegment)
        db.session.flush()
        nonSilentSegment_id = nonSilentSegment.id

        if length <= max_len:
            start, length = int(seg['start']), int(seg['end'] - seg['start'])
            create_cgsegment_cgtask_file(audiofile_id, patient_name, audio_filename, nonSilentSegment_id, start, length,
                                         sr, start_time_audiofile)
        else:
            quotient = int(length // ideal)
            remainder = length % ideal

            if remainder >= min_len:
                for i in range(quotient):
                    start, length = int(seg['start'] + (i * ideal)), int(ideal)
                    create_cgsegment_cgtask_file(audiofile_id, patient_name, audio_filename, nonSilentSegment_id, start,
                                                 length, sr, start_time_audiofile)
                start, length = int(seg['end'] - remainder), int(remainder)
                create_cgsegment_cgtask_file(audiofile_id, patient_name, audio_filename, nonSilentSegment_id, start,
                                             length, sr, start_time_audiofile)
            else:
                for i in range(0, quotient - 1):
                    start, length = int(seg['start'] + (i * ideal)), int(ideal)
                    create_cgsegment_cgtask_file(audiofile_id, patient_name, audio_filename, nonSilentSegment_id, start,
                                                 length, sr, start_time_audiofile)
                start, length = int(seg['end'] - remainder - ideal), int(remainder + ideal)
                create_cgsegment_cgtask_file(audiofile_id, patient_name, audio_filename, nonSilentSegment_id, start,
                                             length, sr, start_time_audiofile)
    db.session.commit()


def _parse_timestamp_from_fname(file_name):
    file_name = os.path.basename(file_name)
    file_name = file_name[file_name.rfind("_") + 1:]
    file_name = file_name.split(".")[0]

    return file_name


def _parse_date_from_file_name(file_name):
    timestamp = _parse_timestamp_from_fname(file_name)
    return datetime.fromtimestamp(float(timestamp) / 1000)


def get_file_path(patient_name, audio_file):
    return WORK_PATH + ORIGINAL_FILES_DIRECTORY + patient_name + '/' + audio_file  # wavs/copd20/3521645712.wav


def make_file(audiofile_id, patient_name, audio_filename, segment_start_time, segment_length, segment_id):
    filepath = WORK_PATH + SEGMENT_FILES_DIRECTORY + str(patient_name) + '/' + str(audiofile_id) + '_' + str(
        segment_id) + '.wav'
    print("............................",filepath)
    # read the original file
    rate, data = wavfile.read(WORK_PATH + ORIGINAL_FILES_DIRECTORY + patient_name + '/' + audio_filename)
    # segment it
    out_file = data[segment_start_time:segment_start_time + segment_length]
    # save it to file
    wavfile.write(filepath, rate, out_file)


def run_silent_remover(patient_name, filename, threshold=0.05e6, overlap_s=0.5, min_seg_len=5, min_non_seg_len=1,
                       plot=False, min_len=5, max_len=15, ideal=10):
    """
    * Run silent remover on a single audiofile
    * Add the audiofile info to the audiofile table
    * Run silent remover on it
    * Add nonsilent segments to nonsilentsegments table
    * Create segments based on nonsilent segments
    * Add segments to cgsegments table

    min_seg_len & min_non_seg_len are used for silent remover algorithm (for creating nonsilentsegments)
    min_len & max_len & ideal are used for creating cg segments based on nonsilentsegments
    """
    audio_path = get_file_path(patient_name, filename)
    print(audio_path)
    audio, sample_rate = read_wave(audio_path)
    audio_len = len(audio)
    start_time_audiofile = _parse_date_from_file_name(filename)
    audiofile_id = addAudioFile(filename, patient_name, audio_len, sample_rate, start_time_audiofile)
    segs = get_noisy_segments(audio, sample_rate, threshold=threshold, overlap_s=overlap_s, plot=plot)
    noisy_segs = smooth_segments(segs, sample_rate, audio_len, min_seg_len=min_seg_len, min_non_seg_len=min_non_seg_len,
                                 plot=plot)
    # print(patient_name, filename, convert_to_seconds(noisy_segs, sample_rate))
    create_segments(noisy_segs, audiofile_id, start_time_audiofile, patient_name, filename, sample_rate, min_len,
                    max_len, ideal)


def roundrobin(*iterables):
    "roundrobin('ABC', 'D', 'EF') --> A D E B F C"
    # Recipe credited to George Sakkis
    num_active = len(iterables)
    nexts = cycle(iter(it).__next__ for it in iterables)
    while num_active:
        try:
            for next in nexts:
                yield next()
        except StopIteration:
            num_active -= 1
            nexts = cycle(islice(nexts, num_active))


def simple_file_retriever():  # no round robin
    # create list of list of tuples: [
    # [(copd20, 1.wav), (copd20, 2.wav), (copd20, 3.wav)], 
    # [(copd21, 1.wav), ...], 
    # [...]
    # ]
    mylist = []
    directories = glob.glob(WORK_PATH + ORIGINAL_FILES_DIRECTORY + "*")  # copd20, copd21, ...
    print(WORK_PATH + ORIGINAL_FILES_DIRECTORY)
    for directory in tqdm.tqdm(directories):
        list_of_patient_dates = []
        # create a directory in segments/copd.. if already doesn't exist
        Path(WORK_PATH + SEGMENT_FILES_DIRECTORY + os.path.basename(directory)).mkdir(parents=True, exist_ok=True)
        for wav in tqdm.tqdm(glob.glob(directory + "/*.wav")):
            list_of_patient_dates.append(_parse_date_from_file_name(os.path.basename(wav)))
            mylist.append((os.path.basename(directory), os.path.basename(wav)))  # ('copd20','1234.wav')

        add_patient(patient_name=os.path.basename(directory), status='enabled', start_date=min(list_of_patient_dates),
                    end_date=max(list_of_patient_dates))

    return mylist


def add_patient(patient_name, status, start_date, end_date):
    patient = Patient(name=patient_name, status=status, start_date=start_date, end_date=end_date)
    db.session.add(patient)
    db.session.commit()


def reset_database():
    # db.session.remove()
    no_delete = ['patient', 'audio_file', 'non_silent_segment', 'cg_segment', 'cg_task', 'user']
    meta = db.metadata
    for table in reversed(meta.sorted_tables):
        if table.name not in no_delete:
            print('Clear table %s' % table)
            db.engine.execute('TRUNCATE TABLE ' + table.name + ' RESTART IDENTITY CASCADE')
            # db.session.execute(table.delete())
    db.session.commit()


# How many files per patient in wavs directory
def _get_num_files_path():
    directories = glob.glob(WORK_PATH + ORIGINAL_FILES_DIRECTORY + "*")
    for directory in directories:
        print(os.path.basename(directory), len(glob.glob(directory + "/*.wav")))


# How many files per patient in db
def _get_num_files_db():
    audiofiles = db.session.query(AudioFile.patient_name, func.count(AudioFile.id)).group_by(
        AudioFile.patient_name).all()
    print(audiofiles)


def _get_duration_all():
    audiofiles = db.session.query(AudioFile.patient_name,
                                  func.sum(AudioFile.length * 1.0 / AudioFile.sample_rate * 1.0)).group_by(
        AudioFile.patient_name).all()
    print(audiofiles)


def _get_duration_non_silent():
    durations = db.session.query(AudioFile.patient_name,
                                 func.sum(NonSilentSegment.length * 1.0 / AudioFile.sample_rate * 1.0)) \
        .outerjoin(NonSilentSegment) \
        .group_by(AudioFile.patient_name) \
        .all()
    print(durations)

def create_myself():
    user = User(firstname='Admin', lastname=' ', email='admin@annotation.com', password=bcrypt.generate_password_hash('adminpwd').decode('utf-8'), role='admin', is_temp_pw=False)
    user2 = User(firstname='a', lastname='a', email='a@a.com', password=bcrypt.generate_password_hash('123').decode('utf-8'), role='annotator', is_temp_pw=False)

    db.session.add(user)
    db.session.add(user2)
    db.session.flush()
    db.session.commit()

def load_data():
    all_files = simple_file_retriever()
    print('####### All files read #########')
    for patient_wav in tqdm.tqdm(all_files):  # ('copd20', 'audio_1480283459342.wav')
        run_silent_remover(patient_wav[0], patient_wav[1])  # run_silent_remover('copd20', 'audio_1480283459342.wav')
    db.session.commit()
    create_myself()
