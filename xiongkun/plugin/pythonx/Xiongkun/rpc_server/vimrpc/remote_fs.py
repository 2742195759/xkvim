import os
import sys
import json
import time
from .decorator import *
from .functions import KillablePool
import os.path as osp
import glob

class RemoteFS:
    @server_function
    def fetch(self, path):
        if not osp.isfile(path):
            return f"Error: no such files: `{path}`"
        with open(path, "r") as fp: 
            lines = fp.readlines()
        return "".join(lines)

    @server_function
    def store(self, path, content):
        if not osp.isfile(path):
            return f"Error: no such files: `{path}`"
        try:
            with open(path, "w") as fp: 
                fp.write(content)
        except: 
            return "failed."
        return "success."

    @server_function
    def list_dir(self, dirpath):
        return os.listdir(dirpath)

    @server_function
    def exists(self, filepath):
        return os.path.exists(filepath)
    
    @server_function
    def tree(self, dirpath):
        def _tree(root):
            ret = {'files': [], 'dirs': []}
            names = os.listdir(root)
            for name in names: 
                path = os.path.join(root, name)
                if os.path.isdir(path):
                    ret['dirs'].append((name, _tree(path)))
                elif os.path.isfile(path):
                    ret['files'].append(name)
            return ret
        return _tree(dirpath)

    @server_function
    def command(self, command_str):
        return os.system(command_str)

if __name__ == "__main__":
    from server_cluster import ServerCluster, printer_process_fn
    servers = ServerCluster()
    servers.start_queue(printer_process_fn)
    #servers.grepfinder = GrepSearcher(servers.queue)
    fn = servers.get_server_fn("remotefs.tree")
    print (fn (1, "/home/data/test/"))
    fn = servers.get_server_fn("remotefs.exists")
    print (fn (1, "/home/data/xxxx"))
    fn = servers.get_server_fn("remotefs.command")
    print (fn (1, "ls /home/data"))
    time.sleep(3)
    servers.stop()

