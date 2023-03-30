import os
import sys
import json
import time
from decorator import *
from log import log
from functions import KillablePool

class Filefinder:
    def __init__(self):
        self.files = ["initializing..."]
        # type is "DIRECTOTYR@TYPE"
        # for example: "/home/data/Paddle/@file|mru"
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
            if 'build/' in filepath: return False
            return True
        self.files = list(filter(filt, self.files))
        log("[FileFinder] set files with length:", len(self.files))
        return None

    @server_function
    def get_type(self):
        return self.type
        
    # TODO: error handle is not prefect
    #       when we have processes: Main -> Search -> Pool, 
    #       when kill the Search Process, Pool Processes will raise a lot of BrokenPipeError
    #       how to ignore them.
    #       Hints: https://stackoverflow.com/questions/11312525/catch-ctrlc-sigint-and-exit-multiprocesses-gracefully-in-python
    #@server_function
    @process_function 
    def search(self, search_text): 
        # map and calculate
        num_worker=20
        with KillablePool(num_worker) as p:
            inputs = default_map_fn(1, num_worker, search_text, self.files)
            outputs = p.map(fuzzy_match_pool, inputs)
        # reduce and post handle.
        # fuzzy map on the returned value.
        gather = []
        for output in outputs: 
            res, _ = output
            if not res: continue
            gather.extend(res)
        return fuzzy_match(search_text, gather)

def fuzzy_match_pool(args):
    """
    Pool().map don't unpack automatic, so we should have list as a parameter.
    """
    return fuzzy_match(*args)

def fuzzy_match(search_text, candidate):
    assert candidate is not None, "candidate is None, error!"
    import glob
    import re
    join = []
    if isinstance(search_text, tuple): 
        search_text = search_text[0]
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
        res = list(fuzzyfinder(search_base, filter(filt, candidate)))[:17]
    if search_base is None: 
        return [], None
    return res, search_base

def test_main():
    f = Filefinder()
    search = "it"
    inputs = ["xxxx", "hhhh", "getit"] * 100000
    f.files = inputs
    print(f.search(1, search))
    #from queue_loop import queue
    #print(queue.get())

if __name__ == "__main__":
    test_main()
