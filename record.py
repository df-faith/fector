from threading import Thread, Lock
import socket
import subprocess
import time

from queue import Queue
from tqdm import tqdm

import misc 
import config
from misc import *
from input import InputThread
from parse import ParserThread

path_prefix = "./events/"

class SshEvent():
    def __init__(self, path, clean=None):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn = self.sock.connect(config.ssh_gateway)
        self.clean_script = None
        path = path_prefix + path
        with open(path, 'r') as f:
            self.script = f.read()
        if clean is not None:
            with open(path_prefix + clean , 'r') as f:
                self.clean_script = f.read()

    def perform(self):
        #self.sock.send(self.script.encode())
        # for line in self.script:
        #     self.sock.send(line.encode())
        #     time.sleep(0.1)
        try:
           # self.sock.send(self.clean_script.encode())
            self.sock.send(self.script.encode())
        except:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conn = self.sock.connect(config.ssh_gateway)
            self.sock.send(self.script.encode())

    def must_clean(self):
        if self.clean_script is None:
            return False
        else:
            return True

    def clean(self):
        try:
            self.sock.send(self.clean_script.encode())
        except:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.conn = self.sock.connect(config.ssh_gateway)
            self.sock.send(self.clean_script.encode())

class ScriptEvent():
    def __init__(self, path, clean=None):
        self.clean = None
        self.path = path_prefix + path


    def perform(self):
        subprocess.Popen(self.path, shell=False)

    def must_clean(self):
        if self.clean is None:
            return False
        else:
            return True

class RecordWriter(Thread):
    @classmethod
    def get_record_name(cls, event):
        event = load_event(event)
        return config.rec_dir + 'rec_%s_%s.json' % (event['id'], event['name'])

    def __init__(self, event, queue, rounds):
        super().__init__()
        self.event = load_event(event)
        self.queue = queue
        self.rounds = rounds
        self.lock = Lock()
        self.die = False
        self.records = []
        return

    def stop(self):
        self.die = True

    def plausibility_check(self, d):
        i = 0
        avg = 0.
        for round in d:
            avg = avg + ((1. / (i + 1)) * (len(d[round]) - avg))
            i += 1
        logging.info("Average round size: %d" % (avg))

        for round in d:
            if abs(len(d[round]) - avg) > (avg * 0.1):
                logging.info("Uncommon round size in round: %s: %d" % (round, len(d[round])))


    def reformat_records(self):
        """Transforms into a round-based dict"""

        d = {}
        for r in self.records:
            cur_round = r['round']
            if cur_round not in d:
                d[cur_round] = [r]
            else:
                d[cur_round].append(r)

        #self.plausibility_check(d)
        return d


    def run(self):
        rec_name = RecordWriter.get_record_name(self.event)
        while True:
            try:
                self.records.append(self.queue.get(timeout=5))
                self.queue.task_done()
            except Exception as e:
                with self.lock:
                    if self.die is True:
                        break
                continue

        with open(rec_name, 'w') as f:
            res = {}
            res['rounds'] = self.rounds
            res['records'] = self.reformat_records()
            f.write(json.dumps(res, indent=4))


def record(event, n=None):
    """Records the given event. The argument should be either the ID or the name.
    n is the number of rounds, how often the event shall be performed and recorded."""

    if n is None:
        n = config.default_n

    # load event
    event_d = misc.load_event(event)
    if event_d is None:
        print("[Failed] Event " + str(event) + " not found!")
        return None

    if "delta_t" in event_d:
        delta_t = event_d['delta_t']
    else:
        delta_t = config.default_time

    if 'ssh' in event_d:
        clean = None
        if "clean" in event_d:
            clean = event_d['clean']
        action = SshEvent(event_d['ssh'], clean)
    else:
        # TODO Clean for CLI events
        action = ScriptEvent(event_d['script'])

    # Queues for communication
    input_queue = Queue()
    parser_queue = Queue()

    # Create Threads
    # 1. WriterThread
    writer_thread = RecordWriter(event_d, parser_queue, n)
    writer_thread.start()

    # 2. ParserThread
    parser_thread = ParserThread(input_queue, parser_queue)
    parser_thread.start()

    # 3. InputThread
    record_thread = InputThread(input_queue, learn=True)
    record_thread.start()

    must_clean = action.must_clean()

    for i in tqdm(range(0, n), desc="rounds"):
        # 1) perform action
        action.perform()

        # 2) wait
        time.sleep(delta_t)

        if must_clean is True:
            # 2.1 Pause Thread
            record_thread.pause()

            # 2.2 Clean
            action.clean()

            # 2.3 wait
            time.sleep(delta_t)

        # 3) increment round
        record_thread.increment_round()

    record_thread.stop()
    parser_thread.stop()
    writer_thread.stop()

    record_thread.join()
    parser_thread.join()
    writer_thread.join()
