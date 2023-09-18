import os
import sys
import json
import time
from .decorator import *
from .functions import KillablePool
from .fuzzy_list import FuzzyList
from .utils import GetSearchFiles

class FileFinder(Service):
    def __init__(self, queue, ppool):
        self.queue = queue
        self.ppool = ppool
        self.root = None
        self.fuzzy = FuzzyList(self.queue, ppool)

    @server_function
    def set_root(self, rootpath, force=False):
        if not force and self.root == rootpath: 
            return self.files[:17]
        self.root = rootpath
        self.files = GetSearchFiles(self.root)
        self.files = [ file[len(self.root)+1:] for file in self.files ] # remove directory
        # TODO: find files and reset it.
        self.fuzzy.set_items(-1, "filefinder", self.files)
        return self.files[:17]

    # transfer only
    def search(self, id, name, search_text):
        return self.fuzzy.get_service("search")(id, 'filefinder', search_text)

def test_main():
    from server_cluster import ServerCluster, printer_process_fn
    import multiprocessing as mp
    mp_manager = mp.Manager()
    servers = ServerCluster(mp_manager)
    servers.start_queue(printer_process_fn)
    #servers.grepfinder = GrepSearcher(servers.queue)
    fn = servers.get_server_fn("filefinder.set_root")
    fn (1, "/home/xiongkun/xkvim/", True)
    fn = servers.get_server_fn("filefinder.search")
    fn (2, "xxx", "rpc_server")
    fn (3, "xxx", "file_finder.py")
    time.sleep(3)
    servers.stop()

if __name__ == "__main__":
    print ("start test filefinder.py")
    test_main()
