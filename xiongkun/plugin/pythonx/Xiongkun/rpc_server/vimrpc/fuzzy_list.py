import os
import sys
import json
import time
from .decorator import *
from .functions import KillablePool

class FuzzyList(AsyncServer):
    def __init__(self, queue, ppool):
        """ 
        Save a mapping from: name:String -> items:List(String)
        """
        self.queue = queue
        self.ppool = ppool
        self.lists_dict = {}

    @server_function
    def set_items(self, name, items): 
        self.lists_dict[name] = items
        return None

    @server_function
    def is_init(self, name, hashid):
        return name in self.lists_dict and hash(tuple(self.lists_dict[name])) == hashid
        
    # TODO: error handle is not prefect
    #       when we have processes: Main -> Search -> Pool, 
    #       when kill the Search Process, Pool Processes will raise a lot of BrokenPipeError
    #       how to ignore them.
    #       Hints: https://stackoverflow.com/questions/11312525/catch-ctrlc-sigint-and-exit-multiprocesses-gracefully-in-python
    #@server_function
    @async_function 
    def search(self, name, search_text): 
        # map and calculate
        num_worker=20
        files = self.lists_dict.get(name, [])
        with KillablePool(num_worker) as p:
            inputs = default_map_fn(1, num_worker, search_text, files)
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
        # speed of fuzzyfind is limited by len(filepath), speed up from 20s -> 1s
        if (len(filepath) > 100): return False
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
    f = FuzzyList()
    search = "it"
    inputs = ["xxxx", "hhhh", "getit"] * 100000
    f.files = inputs

if __name__ == "__main__":
    test_main()

