import json
import re
from queue import Queue, Empty

from threading import Thread, Lock

import config
from message import message_fields

_parser_dict = {
    'Source': 'source',
    'source': 'source',
    'TypeID': 'type_id',
    'type_id': 'type_id',
    'syscall_nr': 'type_id',
    'Path': 'path',
    'path': 'path',
    'args': 'misc',
    'ProcessID': 'pid',
    'pid': 'pid',
    'proc_name': 'process_name',
    'ProcessName': 'process_name',
    'program' : 'process_name',
    'args': 'misc',
    'round': 'round',
    'user' : 'user',
    'User' : 'user'
}

class ParserThread(Thread):
    def __init__(self, in_queue, out_queue):
        super().__init__()
        self.dictionary = {}
        self._load_regexps()
        self.in_queue = in_queue
        self.out_queue = out_queue
        self.die = False
        self.lock = Lock()

    def _load_regexps(self):
        for f in config.parser_files.keys():
            with open(config.parser_files[f], 'r') as regex_file:
                r = json.load(regex_file)
                self.dictionary[f] = r

    def _parse_txt(self, msg):
        if msg['source'] in self.dictionary.keys():
            d_list = self.dictionary[msg['source']]
        else:
            logging.info("No dictionary found for %s)" % msg['source'])
            return msg

        # Iterate over regular expressions
        for msg_type in d_list:
            regex = msg_type['regex']

            txt_msg = msg['raw_message']
            match = re.match(regex, txt_msg)
            if match is not None:
                # Iterate over fields
                for field_name in msg_type:
                    if field_name == "type_id":
                        msg["type_id"] = int(msg_type["type_id"])
                        continue
                    elif field_name == "regex":
                        continue
                    index = int(msg_type[field_name])
                    if index == -1:
                        continue
                    msg[field_name] = match.group(index)
                return msg

        #print(f"Could not parse {msg}")
        return msg


    def _parse_dict(self, msg):
        res = {}
        for k in msg.keys():
            if k in _parser_dict:
                if k == "TypeID" or k == "type_id" or k == "round":
                    res[_parser_dict[k]] = int(msg[k])
                else:
                    res[_parser_dict[k]] = str(msg[k])
            elif type(msg[k]) is dict:
                rec = self._parse_dict(msg[k])
                res = {**rec, **res}


        return res

    def _parse(self, msg):
        res = self._parse_dict(msg)
        if 'message' in msg.keys():
            res['raw_message'] = msg['message']
        if res['source'] != 'sys_syscall_ubuntu1604':
            res = self._parse_txt(res)

        return res

    def stop(self):
        with self.lock:
            self.die = True

    def run(self):
        while True:
            try:
                msg = self.in_queue.get(timeout=5)
                res = self._parse(msg)
                self.in_queue.task_done()
                self.out_queue.put(res)
            except Empty as e:
                with self.lock:
                    if self.die is True:
                        return
            except Exception as e:
                raise e
