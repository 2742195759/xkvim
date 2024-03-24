import os
import sys
import json
import time
from .decorator import *
from .functions import KillablePool
from .utils import GetSearchGrepArgs, GetSearchConfig, escape, GetConfigByKey, AddAbbreviate
import os.path as osp
import subprocess
from .sema.sema import SemaPool, LinePos

class ProjectConfigure(Service):
    def __init__(self, queue):
        self.queue = queue

    @server_function
    def get_config_by_key(self, key, directory):
        return GetConfigByKey(key, directory)

    @server_function
    def set_config_by_key(self, directory, key, val):
        try: 
            AddAbbreviate(key, val, directory)
            return ""
        except Exception as e: 
            return f"{str(e)}"
        
def test_main():
    from server_cluster import ServerCluster, printer_process_fn
    mp_manager = mp.Manager()
    servers = ServerCluster(mp_manager)
    servers.start_queue(printer_process_fn)
    #servers.grepfinder = GrepSearcher(servers.queue)
    fn1 = servers.get_server_fn("config.set_config_by_key")
    fn2 = servers.get_server_fn("config.get_config_by_key")
    print (fn1 (1, "/home/data/" ,"xxxx", "xkxkxk"))
    print (fn2 (2, "terminal_abbreviate", "/home/data/"))
    time.sleep(3)
    servers.stop()

if __name__ == "__main__":
    print ("start test config server.")
    test_main()


