from threading import Thread
import os
import json
import logging

import config
import misc
import fingerprint

def get_all_other_event_ids(event_id, events=None):
    if type(event_id) is dict:
        event_id = event_id['id']

    if events is None:
        with open(config.events_file) as f:
            events = json.load(f)
    else:
        e_list = []
        for e in events:
            e_list.append(misc.load_event(e))
        events = e_list

    result = []
    for e in events:
        if e['id'] == event_id:
            continue
        if e['id'] == 100:
            continue
        result.append(e['id'])

    return result

def get_same_class_events(event_id, events=None):
    if type(event_id) is dict:
        event_id = event_id['id']

    if events is None:
        with open(config.events_file) as f:
            events = json.load(f)
    else:
        e_list = []
        for e in events:
            e_list.append(misc.load_event(e))
        events = e_list

    event = misc.load_event(event_id)

    result = [] 
    for e in events:
        if e['id'] == event_id:
            continue
        if e['id'] == 100:
            continue
        if e['class'] == event['class']:
            result.append(e['id'])

    return result

class CharacteristicFingerprint(Thread):
    @classmethod
    def get_cfingerprint_name(cls, event, features, reference_set):
        event = misc.load_event(event)
        f_list = ""
        for f in features:
            f_list += f + '-'
        f_list = f_list[:-1]

        ref_list = ""
        for ref in reference_set:
            ref_list += str(ref) + '-'
        ref_list = ref_list[:-1]

        fn = config.cfp_dir + "cfp_%d_%s_%s_%s.json" % (event['id'], event['name'], f_list, ref_list)

        return fn


    def __init__(self, fingerprint, reference_set, save=True, load_saved=True):
        super().__init__()
        self.result = None
        self.fingerprint = fingerprint # the fingerprint should be a dict!
        if type(fingerprint) != dict:
            logging.error("[Error] The type of the fingerprint should be a dict!")
            logging.error(type(fingerprint))
            return
        self.event_id = fingerprint['event_id']
        self.features = self.fingerprint['features']
        self.cfp_name = CharacteristicFingerprint.get_cfingerprint_name(self.event_id, self.features, reference_set)
        self.reference_set = reference_set
        self.save = save
        self.load_saved = load_saved

    def run(self):
        if self.load_saved is True:
            if self.load_cfingerprint() is True:
                return
            else:
                self.cfingerprint()
        else:
            self.cfingerprint()

        if self.save is True:
            self.write_cfingerprint()

    def cfingerprint(self):
        self.result = {}
        self.result['event_id'] = self.event_id
        self.result['characteristic'] = True
        self.result['reference_set'] = self.reference_set
        self.result['threshold'] = self.fingerprint['threshold']
        self.result['features'] = self.features
        self.result['delta_t'] = self.fingerprint['delta_t']
        self.result['vectors'] = list(self.fingerprint['vectors']) # copies the fingerprint vectors

        # load other fingerprints
        reference_fps = []
        for ref_id in self.reference_set:
            reference_fps.append(fingerprint.load_fingerprint_as_dict(ref_id, self.features))

        try:
            for ref_fp in reference_fps:
                for v_ref in ref_fp['vectors']:
                    for v in self.result['vectors']:
                        if fingerprint.Fingerprint.cmp_fv(v_ref, v, self.features):
                            self.result['vectors'].remove(v)
        except:
            return


    def load_cfingerprint(self):
        if os.path.isfile(self.cfp_name):
            with open(self.cfp_name, 'r') as f:
                logging.info("[Info] Loading fingerprint from file: %s" % (self.cfp_name))
                self.result = json.load(f)
                return True
        else:
            logging.info("[Info] Could not load %s" % (self.cfp_name))
            return False


    def write_cfingerprint(self):
        if self.result is None:
            logging.error("Could not write characteristic fingerprint!")
            return

        with open(self.cfp_name, 'w') as f:
            json.dump(self.result, f, indent=4)


def load_cfp(event, features, reference_set):
    fn = CharacteristicFingerprint.get_cfingerprint_name(event, features, reference_set)

    if os.path.isfile(fn):
        with open(fn, 'r') as f:
            logging.info("[Info] Loading fingerprint from file: %s" % (fn))
            return json.load(f)
    else:
        print("[Info] Could not load %s" % (fn))
        return None

def load_cfingerprint_as_dict(event, features=None):
    """Shortcut to load a cfingerprint"""

    if features is None:
        event = misc.load_event(event)
        try:
            features = event['features']
        except:
            print(f"[Warning] No features set for event {event['name']}")
            return None

    cfp_name = CharacteristicFingerprint.get_cfingerprint_name(event, features)
    
    return fingerprint.load_fingerprint_file(cfp_name)

