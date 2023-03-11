import os
import sys
import json
import time

import os
from threading import Lock, Thread
import multiprocessing as mp
HOME_PREFIX=os.environ["HOME"]

mutex = Lock()
debug = 1
queue = mp.Queue()
class InQueue:
    pass

def process_function(func):
    p = None
    def wrapper(*args):
        self = args[0]
        id = args[1]
        args = args[2:]
        def worker(*args):
            output = func(*args)
            queue.put((id, output))
        nonlocal p
        if p is not None: 
            p.terminate()
        p = mp.Process(target=worker, args=(self, args))
        p.start()
        return InQueue()
    return wrapper

def server_function(func):
    def wrapper(*args):
        self = args[0]
        id = args[1]
        args = args[2:]
        def worker(*args):
            output = func(*args)
            return output
        return worker(self, *args)
    return wrapper

def log(*args):
    if debug == 0: return
    with mutex:
        out = " ".join([a.__str__() for a in args])
        with open(f"{HOME_PREFIX}/vim_log.txt", "a") as fp :
            fp.writelines([out])
            fp.write("\n")

def log_google(*args):
    with mutex:
        out = " ".join([a.__str__() for a in args])
        with open(f"{HOME_PREFIX}/google.txt", "a") as fp :
            fp.writelines([out])
            fp.write("\n")

def send(obj):
    #log("[Server] send: ", json.dumps(obj))
    mutex.acquire()
    print (json.dumps(obj))
    print ("\n")
    sys.stdout.flush()
    mutex.release()

def echo(s):
    return s

class Filefinder:
    def __init__(self):
        self.files = None
        self.type = "none"

    @server_function
    def set_files(self, type, files): 
        self.files = files
        self.type = type
        def filt(filepath):
            basename = os.path.basename(filepath).lower()
            if basename.startswith("."): return False
            if basename.endswith(".o"): return False
            if basename.endswith(".pyc"): return False
            if basename.endswith(".swp"): return False
            if '.git/' in filepath: return False
            return True
        self.files = list(filter(filt, self.files))
        log("[FileFinder] set files with length:", len(self.files))
        return None

    @server_function
    def get_type(self):
        return self.type
        

    @process_function
    def search(self, search_text): 
        assert self.files is not None, "self.files is None, error!"
        import glob
        import re
        join = []
        for t in search_text: 
            if t == '+' or t == '-': join.append("|"+t)
            else: join.append(t)
        search_text = "".join(join)
        pieces = search_text.split("|")
        qualifier = []
        qualifier_name_set = set()
        search_base = None
        for p in pieces: 
            p = p.strip()
            if not p: continue
            if p.startswith("+") or p.startswith("-"): 
                qualifier.append(p)
                qualifier_name_set.add(p)
            else: search_base = p
        if ".git/" not in qualifier_name_set: 
            qualifier.append("-git/")
        if "/build" not in qualifier_name_set: 
            qualifier.append("-/build")
        if "cmake/" not in qualifier_name_set: 
            qualifier.append("-cmake/")

        def filt(filepath): 
            basename = os.path.basename(filepath).lower()
            filepath = filepath.lower()
            for qual in qualifier: 
                if qual.startswith("+") and not re.search(qual[1:], filepath): return False
                if qual.startswith("-") and re.search(qual[1:], filepath): return False
            return True

        if search_base is not None: 
            from fuzzyfinder import fuzzyfinder
            #self.files = list(map(lambda x: os.path.basename(x).lower(), self.files))
            res = list(fuzzyfinder(search_base, filter(filt, self.files)))[:17]
        if search_base is None: 
            return [], None
        return res, search_base

filefinder = Filefinder()

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

def QueueLoop():
    log("[Server]: Start queue loop.")
    while True:
        output = queue.get()
        log("[Server]: Queue Get!")
        send(output)

queue_thread = Thread(target=QueueLoop, args=[], daemon=True).start()

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
    log("Start New Loop")
