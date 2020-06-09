from kafka import KafkaProducer
import json
import time
import sys

import config

class _KafkaWriter():
    def __init__(self):
        c = config.kafka_config
        self.producer = KafkaProducer(bootstrap_servers=[(('%s:%d') % (c['host'], c['port']))])

    def write(self, topic, msg):
        self.producer.send(topic, msg)
        time.sleep(1)


class SyscallTracer():
    def __init__(self, writer=None):
        if writer is None:
            self.writer = _KafkaWriter()
        else:
            self.writer = writer
        self.topic = 'command'

    def _gen_msg(self):
        msg = {}
        msg['plugin'] = 'SyscallLogger'
        msg['command_id'] = '0'
        msg['params'] = None
        msg['vm_id'] = 'ubuntu1604'

        return msg

    def enable_syscalls(self, syscall_list):
        msg = self._gen_msg()
        msg['command'] = 'Trace'
        msg['params'] = [str(x) for x in syscall_list]

        self.writer.write(self.topic, json.dumps(msg).encode())


    def disable_syscalls(self, syscall_list):
        msg = self._gen_msg()
        msg['command'] = 'Untrace'
        msg['params'] = [str(x) for x in syscall_list]

        self.writer.write(self.topic, json.dumps(msg).encode())

def enable_syscalls(syscalls=list(range(0,320))):
    tracer = SyscallTracer().enable_syscalls(syscalls)

def disable_syscalls(syscalls=list(range(0,320))):
    tracer = SyscallTracer().disable_syscalls(syscalls)


# Test
if __name__ == '__main__':
    relevant_syscalls = [2, 4, 40, 59, 122, 123, 209, 42, 113, 114, 49, 85, 90, 161, 176, 294, 313]
    set_a = [4, 40, 59, 122, 123, 209, 42, 113, 114, 49, 85, 90, 161, 176, 294, 313]
    set_b = [2, 40, 59, 122, 123, 209, 42, 113, 114, 49, 85, 90, 161, 176, 294, 313]
    set_c = [40, 59, 122, 123, 209, 42, 113, 114, 49, 85, 90, 161, 176, 294, 313]
    all_syscalls = [*range(0,320)]

    class TestWriter():
        def write(self, topic, msg):
            print("Topic: %s" % topic)
            print("Message: %s" % msg)
    #w = TestWriter()
    w =  _KafkaWriter()
    s = SyscallTracer(writer=w)

    if len(sys.argv) > 1:
        if sys.argv[1] == 'd':
            s.disable_syscalls(all_syscalls)
            time.sleep(1)
        if sys.argv[1] == 'all':
            s.enable_syscalls(all_syscalls)
            time.sleep(1)
        if sys.argv[1] == 'a':
            s.enable_syscalls(set_a)
            time.sleep(1)
        if sys.argv[1] == 'b':
            s.enable_syscalls(set_b)
            time.sleep(1)
        if sys.argv[1] == 'c':
            s.enable_syscalls(set_c)
            time.sleep(1)

    else:
        s.enable_syscalls(relevant_syscalls)
        time.sleep(1)
