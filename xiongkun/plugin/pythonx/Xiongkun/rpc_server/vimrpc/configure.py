import os
import sys
import json
import time
from .decorator import *
from .functions import KillablePool
from .utils import GetSearchGrepArgs, GetSearchConfig, escape, GetConfigByKey
import os.path as osp
import subprocess
from .sema.sema import SemaPool, LinePos

class ProjectConfigure(Service):
    def __init__(self, queue):
        self.queue = queue

    @server_function
    def get_config_by_key(self, key, directory):
        return GetConfigByKey(key, directory)
        
def test_main():
    from server_cluster import ServerCluster, printer_process_fn
    servers = ServerCluster()
    servers.start_queue(printer_process_fn)
    #servers.grepfinder = GrepSearcher(servers.queue)
    fn = servers.get_server_fn("config.get_config_by_key")
    print (fn (1, "terminal_abbreviate", "/root/xkvim/"))
    time.sleep(3)
    servers.stop()

if __name__ == "__main__":
    print ("start test grep search.py")
    test_main()


