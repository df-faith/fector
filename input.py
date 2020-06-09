import threading
from threading import Thread
import json

import config
from queue import Queue

class InputThread(Thread):
    """
    Record messages from an input iterator.

    The messages are written to the out_queue.

    Arguments:
        input (iterator): The input where the results comes from. The iterator shall generate a StopIteration exception
            after a specific amount of time.

    """
    def __init__(self, out_queue, it=None, learn=False):
        """Input is the iterator, e.g., the Kafka Consumer object"""
        super().__init__()
        if it is None:
            self.it = config.get_default_it()
        else:
            self.it = it

        self.out_queue = out_queue
        self.learn = learn
        self.lock = threading.Lock()
        self.record = True
        self.halt = False
        self.current_n = 0

    def record(self):
        with self.lock:
            self.record = True

    def pause(self):
        with self.lock:
            self.record = False

    def stop(self):
        with self.lock:
            self.halt = True

    def increment_round(self):
        """Increment the record round and start record"""
        with self.lock:
            self.current_n += 1
            self.record = True

    def run(self):
        while True:
            for m in self.it:
                try:
                    msg_d = json.loads(m.value.decode('utf-8'))
                except Exception as e:
                    # print("[Input Error] Could not parse:")
                    # print(m.value)
                    continue


                msg_d['source'] = m.topic

                if self.learn is True:
                    with self.lock:
                        msg_d['round'] = self.current_n
                        # should the thread pause?
                        if self.record is False:
                            continue
                with self.lock:
                    # should the thread pause?
                    if self.record is False:
                        continue
                    # should the thread die?
                    if self.halt is True:
                        self.out_queue.put(msg_d)
                        print("Halt is True!")
                        return
                # Finally, output
                self.out_queue.put(msg_d)

            # Check if we have to die
            if self.halt is True:
                return
