import os
import sys
import json
import time
from .decorator import *
from .functions import KillablePool

class Yiyan:
    def __init__(self, queue):
        self.cmd = f"bash {os.environ['HOME']}/xkvim/bash_scripts/yiyan.sh"
        self.child = None
        self.queue = queue
        pass

    @server_function
    def init_yiyan(self): 
        import subprocess
        # create subprocess
        if self.child is not None: 
            self.child.stdin.close()
        try:
            child = subprocess.Popen(self.cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
            self.child = child
            return "success"
        except:
            return "failed"

    def check_alive(self):
        if self.child is None: return False
        if self.child.poll() is None: return True
        return False

    @server_function
    def query(self, query): 
        if self.check_alive() is False: 
            self.init_yiyan(0)
        query = query.strip("\n\r")
        self.child.stdin.write(query + "\n")
        self.child.stdin.flush()
        lines = []
        while True:
            line = self.child.stdout.readline()
            if line.strip() == "": break
            lines.append(line)
        return lines

def test_main():
    from server_cluster import ServerCluster, printer_process_fn
    servers = ServerCluster()
    servers.start_queue(printer_process_fn)
    #servers.grepfinder = GrepSearcher(servers.queue)
    servers.get_server_fn("yiyan.init_yiyan")(1)
    servers.get_server_fn("yiyan.query")(2, "hello?")
    servers.stop()

if __name__ == "__main__":
    test_main()
