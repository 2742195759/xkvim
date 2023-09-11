import os
import sys
import json
import time
from .decorator import *
from .functions import KillablePool
from .utils import GetSearchConfig, ConvertToRePattern
import os.path as osp
import glob
import re

def get_git_prefix(abspath):
    origin = abspath
    def is_git_director(current):
        return osp.isdir(current) and osp.isdir(osp.join(current, ".git"))
    abspath = osp.abspath(abspath)
    def is_root(path):
        return path in ['/', '~']
    ans = []
    while not is_root(abspath) :
        if is_git_director(abspath): 
            ans.append(abspath)
        abspath = osp.dirname(abspath)
    if len(ans) == 0: 
        #print ("Can't find git in father directory.")
        #can't find a git path, so we return "" to represent no directory.
        return ""
    return ans[-1]

class RemoteFS(Service):
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
            return "failed"
        return "success"

    @server_function
    def timestamp(self, path):
        if not osp.isfile(path):
            return -1
        return osp.getmtime(path)

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
    def isfile(self, filepath: str):
        return os.path.isfile(filepath)

    @server_function
    def isdir(self, filepath: str):
        return os.path.isdir(filepath)

    @server_function
    def exists(self, filepath):
        return os.path.exists(filepath)
    
    @server_function
    def tree(self, dirpath):
        ex_dirs, ex_files = GetSearchConfig(dirpath)
        ex_dirs = list(map (ConvertToRePattern, ex_dirs))
        ex_files = list (map (ConvertToRePattern, ex_files))
        def _ignore(path):
            is_dir = osp.isdir(path)
            if is_dir: 
                path = path + "/"
                for ex_dir in ex_dirs:
                    if re.search(ex_dir, path):  return True
            else: 
                for ex_file in ex_files:
                    if re.search(ex_file, path):  return True
            return False

        def _tree(root):
            ret = {'files': [], 'dirs': []}
            names = os.listdir(root)
            for name in names: 
                path = os.path.join(root, name)
                if os.path.isdir(path) and not _ignore(path):
                    ret['dirs'].append((name, _tree(path)))
                elif os.path.isfile(path) and not _ignore(path):
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
        if suffix:
            tempname += '.' + suffix
        os.system(f"touch {tempname}")
        return tempname

    @server_function
    def git_based_path(self, abspath):
        origin = abspath
        abspath = get_git_prefix(abspath)
        if abspath: 
            return origin[len(abspath):].strip("/")
        return origin

if __name__ == "__main__":
    from server_cluster import ServerCluster, printer_process_fn
    servers = ServerCluster()
    servers.start_queue(printer_process_fn)
    fn = servers.get_server_fn("remotefs.tree")
    print (fn (1, "/home/xiongkun/test/"))
    time.sleep(3)
    servers.stop()

