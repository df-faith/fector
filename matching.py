from threading import Thread, Lock, Timer
import socket
import subprocess
import time
import fnmatch
import os 
from queue import Queue

import config
import misc
from misc import *
from parse import ParserThread
from input import InputThread
from fingerprint import Fingerprint

class Reporter(Thread):
    def __init__(self, queue, callback=None):
        super().__init__()
        self.q = queue
        self.callback = callback
        self.lock = Lock()
        self.halt = False

    def set_callback(self, callback):
        self.callback = callback

    def stop(self):
        with self.lock:
            self.halt = True

    def run(self):
        while True:
            with self.lock:
                if self.halt is True:
                    return
            try:
                msg = self.q.get(timeout=1)
            except:
                continue
            if self.callback is None:
                print("=== Report ===")
                print(msg)
                print("==============")
            else:
                self.callback(msg)

            self.q.task_done()

class Matcher(Thread):
    def __init__(self, input_queue, output_queue, fingerprint, max_ticks=None):
        super().__init__()
        self.tick_cnt = 0
        self.max_ticks = max_ticks
        self.die = False
        self.lock = Lock()
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.fp_filename = fingerprint
        # load fingerprint
        self.fingerprint = misc.load_fp_as_dict(fingerprint)
        self.event = load_event(self.fingerprint['event_id'])
        self.delta_t = self.fingerprint['delta_t']
        self.reference_set = self.fingerprint['reference_set']

        self.fp_vectors = self.fingerprint['vectors']
        self.fp_size = float(len(self.fp_vectors))
        self.matched_vectors = 0

        # data structure: vector, mapped msg, bucket
        self.fp_map = []
        for vector in self.fp_vectors:
            self.fp_map.append([vector, None, None])

        self.slice = 0

        # set timer
        self.timer = Timer(self.delta_t, self.tick)

    def die(self):
        with self.Lock:
            self.die = True

    def report(self):
        result = {}
        result['event_id'] = self.event['id']
        result['event_name'] = self.event['name']
        result['fingerprint'] = os.path.basename(self.fp_filename)
        result['features'] = self.fingerprint['features']
        result['reference_set'] = self.reference_set
        result['tick'] = self.tick_cnt
        result['total_size'] = self.fp_size
        result['matched'] = self.matched_vectors
        result['score'] = self.score
        self.output_queue.put(result)

    def tick(self):
        # check if we can report
        with self.lock:
            self.tick_cnt += 1
            if self.max_ticks == self.tick_cnt:
                self.die = True

            self.score = self.matched_vectors / self.fp_size
            #if (matched_vectors / self.fp_size) >= config.matching_threshold:
            # for the evaluation, every tick is reported!
            self.report()

            # clear slice
            for v in self.fp_map:
                if v[2] == self.slice:
                    v[1] = None
                    v[2] = None
                    self.matched_vectors -= 1
            self.slice = (self.slice + 1) % 2

        # set timer, again
        self.timer = Timer(self.delta_t, self.tick).start()

    def run(self):
        if len(self.fp_vectors) == 0:
            return
        self.timer.start()
        while True:
            with self.lock:
                if self.die is True:
                    return
            try:
                msg = self.input_queue.get(timeout=1)
            except:
                continue

            with self.lock:
                for vector in self.fp_map:
                        if Fingerprint.cmp_fv(msg, vector[0], self.fingerprint['features']) is True:
                            # check if vector already matched
                            if vector[1] is None:
                                vector[1] = msg
                                vector[2] = self.slice
                                self.matched_vectors += 1

            self.input_queue.task_done()



lock = Lock()
die = False

def wait_for_matchers(matchers):
    global die
    for m in matchers:
        m[1].join()
        print("Join")
    with lock:
        die = True
    print("Initiate dieing")



def start_matching(matching_files=config.matching_files, callback=None, max_ticks=None):
    #                                                  >matcher
    #   +----------+      +--------+     +-----------+/        \   +---------+
    # --| raw msgs |----> | parser |---> | this func |->matcher -> | Reporter|
    #   +----------+      +--------+     +-----------+\        /   +---------+
    #                                                  >matcher 
    input_q = Queue()  # raw messages (as output)
    parser_q = Queue() # parsed stuff (as output)
    result_q = Queue() # results from the Matcher(s)
    event_ids = misc.event_ids()
    matchers = []

    if matching_files is None:
        matching_files = config.matching_files

    # iterate over fingerprint files
    for f in os.listdir(config.cfp_dir):
        if fnmatch.fnmatch(f, matching_files):
            q = Queue()
            matchers.append((q, Matcher(input_queue=q, output_queue=result_q, fingerprint=config.cfp_dir+f, max_ticks=max_ticks)))
    
    # 1) Start Reporter
    print("Starting Reporter")
    reporter_thread = Reporter(result_q, callback=callback)
    reporter_thread.start()

    # 2) Start all Matcher
    print(f"Start {len(matchers)} Matchers")
    for m in matchers:
        m[1].start()

    # 3) ParserThread
    print("Start Parser")
    parser_thread = ParserThread(input_q, parser_q)
    parser_thread.start()

    # 4) InputThread
    print("Start InputThread")
    input_thread = InputThread(input_q, learn=False)
    input_thread.start()

    # 5) MatcherWaiter
    print("Start Matcher waiters")
    mw = Thread(target=wait_for_matchers, args=(matchers,))
    mw.start()

    # distribute messages
    while True:
        with lock:
            if die is True:
                break
        msg = parser_q.get()
        for m in matchers:
            m[0].put(msg)
        parser_q.task_done()

    mw.join()
    print("Stopping threads")
    input_thread.stop()
    parser_thread.stop()
    reporter_thread.stop()

    print("Waiting for threads")
    input_thread.join()
    parser_thread.join()
    reporter_thread.join()

    return


if __name__ == '__main__':
    start_matching()
