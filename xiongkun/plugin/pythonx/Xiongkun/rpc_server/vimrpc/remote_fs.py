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
        try:
            return os.listdir(dirpath)
        except: 
            return []

    @server_function
    def file_complete(self, leading: str):
        import glob
        files = glob.glob(f"{leading}*")
        def add_slash(file):
            if osp.isdir(file):
                return file + "/"
            return file
        files = list(map(add_slash, files))
        return files

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

    @server_function
    def eval(self, command_str):
        import subprocess
        child = subprocess.Popen(command_str, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        child.stdin.close()
        outputs = [line[:-1] for line in child.stdout.readlines()]
        errors = [line[:-1] for line in child.stderr.readlines()]
        code = child.wait()
        ret = {}
        ret['status'] = 'ok'
        ret['code'] = code
        ret['output'] = outputs
        if code != 0: 
            ret['status'] = 'error'
            ret['error'] = errors
        return ret

    @server_function
    def create_temp_file(self, suffix):
        import tempfile
        tempname = tempfile.mktemp()
        tempname += '.' + suffix
        os.system(f"touch {tempname}")
        return tempname

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

