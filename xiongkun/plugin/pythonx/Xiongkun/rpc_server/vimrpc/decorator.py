import os
import sys
import json
import time

from multiprocessing import Pool
import os
from threading import Lock, Thread
import multiprocessing as mp
from functools import partial
from log import log

class Service:
    def get_service(self, key):
        attr = getattr(self, key)
        return attr

class AsyncServer:
    #def __init__(self, queue, ppool):
        #self.queue = queue
        #self.ppool = ppool
    def get_service(self, key):
        attr = getattr(self, key)
        if hasattr(attr, "__async__") and attr.__async__ is True: 
            new_attr = process_function(self, key, attr)
            setattr(self, key, new_attr)
        elif hasattr(attr, "__stream__") and attr.__stream__ is True: 
            new_attr = stream_decorator(self, key, attr)
            setattr(self, key, new_attr)
        attr = getattr(self, key)
        return attr

class InQueue:
    pass

def async_function(func):
    setattr(func, "__async__", True)
    return func

def stream_function(func):
    setattr(func, "__stream__", True)
    return func

def process_function(this, funcname, func):
    """ process function is a decorator:
        @process_function(func) will make func a non-block callable
    """
    def wrapper(*args):
        id = args[0]
        args = args[1:]
        def worker(*args):
            output = func(*args)
            this.queue.put((id, True, output))
        this.ppool.terminal(this, funcname)
        this.ppool.start_process(this, funcname, target=worker, args=args)
        return InQueue()
    return wrapper

def stream_decorator(this, funcname, func):
    def wrapper(*args):
        def worker(*args):
            output = func(*args)
            this.queue.put((args[0], True, output))
        this.ppool.terminal(this, funcname)
        this.ppool.start_process(this, funcname, target=worker, args=args)
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

def server_function(func):
    def wrapper(*args):
        self = args[0]
        id = args[1]
        args = args[2:]
        def worker(*args):
            output = func(*args)
            return (id, True, output)
        return worker(self, *args)
    return wrapper

def time_consume(func):
    def wrapper(*args):
        start = time.time()
        output = func(*args)
        print("Time:", time.time() - start)
        return output
    return wrapper
