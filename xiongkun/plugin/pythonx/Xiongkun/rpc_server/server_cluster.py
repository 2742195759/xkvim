from __future__ import print_function
import json
import socket
import sys
import threading
from threading import Thread
from vimrpc.fuzzy_list import FuzzyList
from vimrpc.file_finder import FileFinder
from vimrpc.decorator import InQueue, Service, AsyncServer
from vimrpc.remote_fs import RemoteFS
from vimrpc.yiyan_server import Yiyan
from vimrpc.grep_search import GrepSearcher
from vimrpc.hoogle import HoogleSearcher
from vimrpc.configure import ProjectConfigure
import multiprocessing as mp
from log import log

class ProcessManager:
    def __init__(self):
        self.pools = {}

    def terminal_all(self): 
        for p in self.pools.values():
            p.terminate()
            p.join()
        self.pools.clear()

    def terminal(self, server, func_name):
        hashid = hash((id(server), func_name))
        if hashid in self.pools:
            self.pools[hashid].terminate()
            self.pools[hashid].join()
            del self.pools[hashid]

    def start_process(self, server, func_name, target, args):
        hashid = hash((id(server), func_name))
        p = mp.Process(target=target, args=args)
        p.start()
        self.pools[hashid] = p
        return p

class ServerCluster: 
    def __init__(self, queue):
        self.process_manager = ProcessManager()
        self.queue = queue
        self._init_server()
        def keeplive(*a, **kw): 
            return [-1, True, 'ok']
        self.keeplive = keeplive
        self._stop = False

    def _init_server(self):
        self.filefinder = FileFinder(self.queue, self.process_manager)
        self.remotefs = RemoteFS()
        self.fuzzyfinder = FuzzyList(self.queue, self.process_manager)
        self.grepfinder = GrepSearcher(self.queue, self.process_manager)
        self.hoogle = HoogleSearcher(self.queue)
        self.config = ProjectConfigure(self.queue)

    def _QueueLoop(self, process_fn):
        #log("[Server]: Start queue loop.")
        while not self._stop:
            try:
                output = self.queue.get(timeout=1)
                #log(f"[Server]: Queue Get! {output}")
                process_fn(output)
            except Exception as e:
                continue

    def get_server_fn(self, name):
        name = name.strip()
        obj = self
        for f in name.split('.'): 
            if hasattr(obj, f): 
                if isinstance(obj, (Service, AsyncServer)):
                    obj = obj.get_service(f)
                else:
                    obj = getattr(obj, f)
            elif isinstance(obj, dict) and f in obj:
                obj = obj.get(f, None)
            else:
                obj = None
        if callable(obj):
            return obj
        log("[Server]: don't found ", name, ", skip it.")
        return None

    def start_queue(self, sender):
        self.queue_thread = Thread(target=self._QueueLoop, args=[sender], daemon=True)
        self.queue_thread.start()

    def stop(self):
        print ("[ServerCluster] Stop All Processes and Queue.")
        self._stop = True
        self.process_manager.terminal_all()
        self.queue_thread.join()

def printer_process_fn(output):
    print (output)

class YiyanServerCluster(ServerCluster):
    def _init_server(self):
        self.yiyan = Yiyan(self.queue)
