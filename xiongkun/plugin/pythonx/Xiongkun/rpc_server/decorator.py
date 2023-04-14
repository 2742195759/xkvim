import os
import sys
import json
import time

from multiprocessing import Pool
import os
from threading import Lock, Thread
import multiprocessing as mp
from functools import partial
from queue_loop import queue
from log import log

class InQueue:
    pass

def process_function(func):
    """ process function is a decorator:
        @process_function(func) will make func a non-block callable
    """
    p = None
    def wrapper(*args):
        self = args[0]
        id = args[1]
        args = args[2:]
        def worker(*args):
            log("process function with args:", *args)
            output = func(*args)
            queue.put((id, output))
        nonlocal p
        if p is not None: 
            p.terminate()
        args = tuple([self] + list(args))
        p = mp.Process(target=worker, args=args)
        p.start()
        return InQueue()
    return wrapper

def single_pool(func):
    """ process function is a decorator:
        @process_function(func) will make func a non-block callable
    """
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

def default_map_fn(idx, num_worker, *args):
    tosplit = args[idx]
    assert isinstance(tosplit , list)
    length = len(tosplit)
    each_len = length // num_worker + 1
    splited = []
    for i in range(num_worker):
        item = []
        for j in range(len(args)):
            if j != idx: 
                item.append(args[j])
            else:
                piece = tosplit[(i)*each_len:(i+1)*each_len]
                item.append(piece)
        if item[idx]: splited.append(tuple(item))
    return splited

def default_reduce_fn(outputs, *args): 
    ret = []
    for output in outputs:
        ret.extend(output)
    return ret

def pool_function(map_fn, reduce_fn=default_reduce_fn, num_worker=20): 
    def _pool_function(func):
        """ process function is a decorator:
            @pool_function(func) will make func a block parallel-map callable.
        """
        def wrapper(*args):
            def worker(*args):
                with Pool(10) as p:
                    args_list = map_fn(num_worker, *args)
                    outputs = p.map(func, args_list)
                    #outputs = reduce_fn(outputs, *args)
                    return outputs
            return worker(*args)
        return wrapper
    return _pool_function

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

def time_consume(func):
    def wrapper(*args):
        start = time.time()
        output = func(*args)
        print("Time:", time.time() - start)
        return output
    return wrapper
