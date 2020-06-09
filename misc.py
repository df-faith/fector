import json
import config
import os
import logging

feature_sets = [['source', 'type_id'], ['source', 'type_id', 'misc'], ['source', 'type_id', 'path'], ['source', 'type_id', 'path', 'misc']]

def list_events():
    with open(config.events_file) as f:
        events = json.load(f)
        for e in events:
            print(('%d | %s | %s') % (e['id'], e['name'], e['description']))

def load_event(event):
    with open(config.events_file) as f:
        events = json.load(f)

    for e in events:
        if type(event) is int:
            if e['id'] == event:
                return e
        elif type(event) is str:
            if e['name'] == event:
                return e
        elif type(event) is dict:
            # this is the case, when the event has been loaded, before
            return event
    return None

def load_class_events(class_string):
    result = []
    with open(config.events_file) as f:
        events = json.load(f)
        for e in events:
            if e['class'] == class_string:
                result.append(e)

    return result

def event_ids(noise=False):
    l = []
    with open(config.events_file) as f:
        events = json.load(f)
        for e in events:
            if e['id'] != 100 or noise is True:
                l.append(int(e['id']))

    return l

def load_fp_as_dict(fn):
    if os.path.isfile(fn):
        with open(fn, 'r') as f:
            logging.info("[Info] Loading fingerprint from file: %s" % (fn))
            return json.load(f)
    else:
        logging.info("[Info] Could not load %s" % (fn))
        return None
