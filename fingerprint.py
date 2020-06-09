import datetime
import json
from threading import Thread
import os.path

import logging
import config
from misc import load_event
from record import RecordWriter


class ContinueOuter(Exception):
    pass

class Fingerprint(Thread):
    @classmethod
    def get_fingerprint_name(cls, event, features):
        event = load_event(event)
        f_list = ""
        for f in features:
            f_list += f + '-'
        f_list = f_list[:-1]
        return config.fp_dir + "fp_%d_%s_%s.json" % (event['id'], event['name'], f_list)

    @classmethod
    def to_fv(cls, record, features):
        result = {}
        for f in features:
            try:
                result[f] = record[f]
            except KeyError:
                result[f] = None
                continue

        return result

    @classmethod
    def cmp_fv(cls, r1, r2, features):
        for f in features:
            try:
                v1 = r1[f]
            except KeyError:
                v1 = None

            try:
                v2 = r2[f]
            except KeyError:
                v2 = None

            if v1 != v2:
                return False

        return True

    def statistics(self):
        result = {}
        if self.result is None:
            return None
        else:
            result['total_size '] = len(self.result['vectors'])

            source_lens = {}
            for v in self.result['vectors']:
                if v['source'] not in source_lens.keys():
                    source_lens[v['source']] = 1
                else:
                    source_lens[v['source']] += 1
            result['sources'] = source_lens

        return result


    def __init__(self, event, threshold=0.8, features=["source", "type_id"], max_rounds=None, save=False, load_saved=False):
        super().__init__()
        self.event = load_event(event)
        self.features = features
        self.max_rounds = max_rounds
        self.save = save
        self.load_saved = load_saved
        self.result = None
        self.threshold = threshold
        self.delta_t = self.event['delta_t']
        self.fp_name = Fingerprint.get_fingerprint_name(event, features)

    def run(self):
        if self.load_saved is True:
            if self.load_fingerprint() is True:
                return
            else:
                return
                #self.fingerprint()
        else:
            self.fingerprint()


    def fingerprint(self):
        rec_file = RecordWriter.get_record_name(self.event)
        result = {}
        result['event_id'] = self.event['id']
        result['name'] = self.event['name']
        result['max_rounds'] = self.max_rounds
        result['characteristic'] = False
        result['threshold'] = self.threshold
        result['features'] = self.features
        result['delta_t'] = self.delta_t
        result['timestamp'] = str(datetime.datetime.now().isoformat())
        vectors = []


        with open(rec_file, 'r') as record_file:
            rec = json.load(record_file)

            # set total_rounds
            total_rounds = rec['rounds']
            if self.max_rounds is None:
                self.max_rounds = total_rounds
            elif self.max_rounds > total_rounds:
                print("[Warning] Too less recorded rounds: %d, Needed: %d" % (total_rounds, self.max_rounds))
            elif self.max_rounds < total_rounds:
                total_rounds = self.max_rounds

            if rec["records"] is None:
                print("[Warning] No records found in %s." % (rec_file))
            else:
                records = rec["records"]

                # round numbers are strings ...
                for cur_round in records.keys():
                    cur_round_i = int(cur_round)
                    for r in records[cur_round]:
                        occurences = 1

                        o_round_i = cur_round_i + 1
                        while o_round_i < total_rounds:
                            o_round = str(o_round_i)
                            try:
                                for o_r in records[o_round]:
                                    if Fingerprint.cmp_fv(r, o_r, self.features) is True:
                                        occurences += 1
                                        records[o_round].remove(o_r)
                                        raise ContinueOuter
                                o_round_i += 1
                            except ContinueOuter:
                                o_round_i += 1
                                o_round = int(o_round_i)
                                continue
                            except KeyError:
                                o_round_i += 1
                                o_round = int(o_round_i)
                                continue

                        if occurences >= self.threshold*total_rounds:
                            vectors.append(Fingerprint.to_fv(r, self.features))

        result['rounds'] = total_rounds
        result['vectors'] = vectors

        self.result = result

        if self.save is True:
            self.write_fingerprint()


    def load_fingerprint(self):
        if os.path.isfile(self.fp_name):
            with open(self.fp_name, 'r') as f:
                logging.info("[Info] Loading fingerprint from file: %s" % (self.fp_name))
                self.result = json.load(f)
                return True
        else:
            print(("[Info] Could not load %s" % (self.fp_name)))
            return False


    def write_fingerprint(self):
        if self.result is None:
            logging.info("[Warning] Could not write fingerprint!")
            return

        with open(self.fp_name, 'w') as f:
            json.dump(self.result, f, indent=4)

def load_fingerprint_file(file_name):
    if os.path.isfile(file_name):
        with open(file_name, 'r') as f:
            logging.info("[Info] Loading fingerprint from file: %s" % (file_name))
            return json.load(f)
    else:
        logging.info("[Info] Could not load %s" % (file_name))
        return None

def load_fingerprint_as_dict(event, features=None):
    """Shortcut to load a fingerprint"""

    if features is None:
        event = misc.load_event(event)
        features = event['features']

    fp_name = Fingerprint.get_fingerprint_name(event, features)
    
    return load_fingerprint_file(fp_name)
