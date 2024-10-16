import os
import sys
import json
import time

from multiprocessing import Pool
import os
from threading import Lock, Thread
import multiprocessing as mp
from functools import partial
from vimrpc.decorator import InQueue
from server_cluster import ServerCluster
from log import log, mutex

def send(obj):
    print (json.dumps(obj))
    print ("\n")
    sys.stdout.flush()

def echo(s):
    return s

def server_main():
    servers = ServerCluster()
    servers.start_queue(send)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        req = json.loads(line)
        id, name, args = req
        log("[Server] receive: ", id, name)
        func = servers.get_server_fn(name)
        if not func:
            continue
        output = func(id, *args)
        if isinstance(output, InQueue): 
            log("[Server]: process function.")
        else: 
            log("[Server]: normal function.")
            send(output)
    servers.stop()

server_main()
