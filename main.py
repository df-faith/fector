#!/usr/bin/env python3
from IPython import embed
import queue
import logging
import sys

from misc import list_events, load_event, event_ids
import record
import syscalls
import characteristic_fingerprint
import fingerprint

logging.basicConfig(level=logging.INFO, format='%(relativeCreated)6d %(threadName)s %(message)s', filename='fector.log')
logging.info("Starting Fector")


def event(e):
    """Loads the json of an event.

    Arguments:
        e: The event as string (name) or the int (id).
    """
    return load_event(e)

def e(ev):
    """Shortcut to load an event.

    Shortcut for the event() function.

    Arguments:
        ev: The event name (string) or the id (int).
    """
    return event(ev)

def l():
    """Shortcut to get a list of all available events."""
    return list_events()

def li():
    """Shortcut to get a list of all available event ids."""

    return event_ids()

def rec(event, n=None):
    if type(event) is int or type(event) is str:
        event = load_event(event)
    record.record(event, n)

def fp(event, threshold=0.8, features=['source', 'type_id'], load_saved=True, save=True):
    if type(event) is int or type(event) is str:
        event = load_event(event)
    fingerprint = Fingerprint(event, threshold=threshold, features=features, load_saved=load_saved, save=save)
    fingerprint.start()
    fingerprint.join()

    return fingerprint

def es(syscall_list=list(range(0,320))):
    """Shortcut to enable system call tracing"""
    syscalls.enable_syscalls(syscall_list)

def ds(syscall_list=list(range(0,320))):
    """Shortcut to disable system call tracing"""
    syscalls.disable_syscalls(syscall_list)

if __name__ == '__main__':
    embed()
