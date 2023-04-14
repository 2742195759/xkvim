import os
import sys
import json
import time

from multiprocessing import Pool
import os
from threading import Lock, Thread
import multiprocessing as mp
from functools import partial
from file_finder import fuzzy_match_pool
from decorator import InQueue, server_function, pool_function, process_function, default_map_fn, time_consume
from queue_loop import QueueLoop
from fuzzy_list import FuzzyList
from log import log, mutex
from yiyan_server import Yiyan

def send(obj):
    #log("[Server] send: ", json.dumps(obj))
    mutex.acquire()
    print (json.dumps(obj))
    print ("\n")
    sys.stdout.flush()
    mutex.release()

def echo(s):
    return s

fuzzyfinder = FuzzyList()
yiyan = Yiyan()

def get_server_by_name(name):
    name = name.strip()
    obj = globals()
    for f in name.split('.'): 
        if hasattr(obj, f): 
            obj = getattr(obj, f)
        elif isinstance(obj, dict) and f in obj:
            obj = obj.get(f, None)
        else:
            obj = None
    if callable(obj):
        return obj
    log("[Server]: don't found ", name, ", skip it.")
    return None

def server_main():
    queue_thread = Thread(target=QueueLoop, args=[send], daemon=True).start()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        id, name, args = req
        log("[Server] receive: ", id, name)
        func = get_server_by_name(name)
        if not func:
            continue
        output = func(id, *args)
        if isinstance(output, InQueue): 
            log("[Server]: process function.")
        else: 
            log("[Server]: normal function.")
            send([id, output])

server_main()
