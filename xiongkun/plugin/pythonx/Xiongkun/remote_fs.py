import vim
import traceback
from . import vim_utils
import time
from .func_register import vim_register
import threading
import subprocess
from functools import partial
import re
from .log import log
import threading
import os.path as osp
from .rpc import rpc_call, rpc_wait, rpc_server
from .vim_utils import vimcommand, IsBufferExist
import os

def is_buf_remote():
    remote = vim.eval("getbufvar(bufnr(), 'remote')")
    return remote == "remote"

@vim_register(command="RemoteSave")
def RemoteSave(args):
    if is_buf_remote():
        bufname = vim.eval("bufname()")
        filepath = FileSystem().filepath(bufname)
        bufnr = vim.eval(f"bufnr('{bufname}')")
        lines = vim.eval(f"getbufline({bufnr}, 1, '$')")
        vim.command("set nomodified")
        if FileSystem().store(filepath, "\n".join(lines)) is not True: 
            vim.command(f"echom '{FileSystem().last_error()}'")
            vim.command("set modified")
    else:
        vim.command("write")
        
@vim_register(command="RemoteEdit", with_args=True)
def RemoteEdit(args):
    if len(args) == 0: 
        bufname = vim.eval("bufname()")
        filepath = FileSystem().filepath(bufname)
        FileSystem().edit(filepath, force=True)
        return
    FileSystem().edit(args[0])
            
vim_utils.commands(""" 
augroup RemoteWrite
    autocmd!
    autocmd BufWriteCmd * RemoteSave
    autocmd FileChangedRO * set noreadonly
augroup END
    """)


def GoToBuffer(bufnr, method):
    """
    jump to a location.
    supported method: 
    1. 's': split
    2. 'v': vertical
    3. 't': tabe
    4. '.' | 'e': current window
    5. 'p': preview open
    6. 'b': buffer open
    6. 'sb': buffer open
    """
    norm_methods = {
        'e': f'enew\nsetlocal bufhidden=wipe\nkeepjumps b {bufnr}',
        '.': f'enew\nsetlocal bufhidden=wipe\nkeepjumps b {bufnr}',
        't': 'tabe!\nsetlocal bufhidden=wipe\nkeepjumps b {bufnr}'.format(bufnr=bufnr),
        'v': 'vne!\nsetlocal bufhidden=wipe\nkeepjumps b {bufnr}'.format(bufnr=bufnr),
        's': f'keepjumps sb {bufnr}',
        'b': f'keepjumps b {bufnr}',
        'sb': f'keepjumps vertical sb {bufnr}',
    }
    commands = norm_methods[method]
    vim_utils.commands(commands)
    

def GoToLocation(location, method):
    #view_methods = {
        #'e': 'noswapfile e',
        #'.': 'noswapfile e',
        #'p': 'noswapfile pedit',
        #'s': 'noswapfile split',
        #'t': 'noswapfile tabe',
        #'v': 'noswapfile vne',
        #'b': 'noswapfile b',
        #'sb':'noswapfile vertical sb',
    #}
    bufnr = FileSystem().bufload_file(location.getfile())
    GoToBuffer(bufnr, method)
    vimcommand(f":{location.getline()}")
    if location.getcol() != 1:
        vimcommand("normal %d|"%(location.getcol()))
    vimcommand("normal zv")

class Location: 
    def __init__(self, file, line=1, col=1, base=1):
        if isinstance(file, int): 
            file = vim.eval(f"bufname({file})")
        self.full_path = FileSystem().abspath(file)
        self.line = line
        self.col = col
        self.base = base

    def getline(self):  
        return self.line 
    
    def getcol(self):   
        return self.col

    def getfile(self):
        return self.full_path

    def to_base(self, new_base):
        col = self.col + new_base - self.base
        row = self.line + new_base - self.base
        return Location(self.full_path, row, col, new_base)

    def jump(self, cmd="."):
        GoToLocation(self, cmd)


def HasSwapFile(path):
    abspath = os.path.abspath(path)
    basename = os.path.basename(abspath)
    pattern = os.path.dirname(abspath) + "/." + basename + ".*"
    import glob
    if len(glob.glob(pattern)): 
        return True
    return False


@vim_register(command="GotoFile", keymap="gf")
def GotoFile(args):
    filepath = vim.eval('expand("<cfile>")')
    FileSystem().edit(filepath)

class DirectoryTree:
    def __init__(self, type, fullpath):
        self.child = []
        self.father = None
        self.type = type
        self.fullpath = fullpath
        self.is_open = False

    def add_child(self, tree):
        self.child.append(tree)
        tree.father = self

    def files(self):
        return [ item for item in self.child if item.type == 'file' ]

    def dirs(self):
        return [ item for item in self.child if item.type == 'dir' ]

    @staticmethod
    def from_dict(fullpath, content):
        this = DirectoryTree("dir", fullpath)
        for dir in content['dirs']:
            name, dircontent = dir
            if name.startswith('.'): continue
            this.add_child(DirectoryTree.from_dict(os.path.join(fullpath, name), dircontent))
        for file in content['files']: 
            if file.startswith('.'): continue
            this.add_child(DirectoryTree("file", os.path.join(fullpath, file)))
        return this

    def __eq__(self, other):
        return other.fullpath == self.fullpath

    def find_by_fullpath(self, fullpath):
        def _find(cur, fullpath):
            if fullpath == cur.fullpath: return cur
            for child in cur.child: 
                if fullpath.startswith(child.fullpath): 
                    return _find(child, fullpath)
        return _find(self, fullpath)

    def open_path(self, node):
        while node.father is not self: 
            node.father.is_open = True
            node = node.father


@vim_utils.Singleton
class FileSystem:
    def __init__(self):
        self._last_error = ""
        self._is_remote = None
        self.cwd = None
        from .rpc import remote_project
        if remote_project is not None:
            print ("RemoteFileSystem Mounted.")
            self.prefix = ""
            self.cwd = remote_project.root_directory
            self._is_remote = True
        else: 
            print ("localFileSystem Mounted.")
            self.prefix = ""
            self.cwd = vim.eval("getcwd()")
            self._is_remote = False

    def is_remote(self):
        return self._is_remote

    def last_error(self):
        return self._last_error

    def store(self, filepath, content):
        assert isinstance(content, (list, str))
        if isinstance(content, list):
            content = "\n".join(content)
        msg = rpc_wait("remotefs.store", filepath, content)
        if msg != "success.": 
            self._last_error = msg
            return False
        return True

    def fetch(self, filepath):
        content = rpc_wait("remotefs.fetch", filepath)
        return content

    def abspath(self, filepath):
        if filepath.startswith("/"): return filepath
        else: return os.path.join(self.getcwd(), filepath)

    def bufname(self, filepath):
        abspath = self.abspath(filepath)
        return self.prefix + abspath

    def filepath(self, bufname):
        if bufname.startswith(self.prefix): 
            return bufname[len(self.prefix):]
        return bufname

    def bufload_file(self, filepath, force=False):
        bufname = self.bufname(filepath)
        def do_open(content): 
            tmp_file = vim_utils.TmpName()
            with open(tmp_file, "w") as f: 
                f.write(content)
            bufnr = vim.eval(f'bufadd("{bufname}")')
            with vim_utils.CurrentBufferGuard():
                vim.eval(f"setbufvar({bufnr}, '&buftype', 'acwrite')")
                vim.eval(f"setbufvar({bufnr}, '&buflisted', 1)")
                vim.command(f"keepjumps b {bufnr}")
                vim.command(f"keepjumps normal ggdG")
                vim.command(f"keepjumps read {tmp_file}")
                vim.command("keepjumps normal ggdd")
                vim.command("set nomodified")
                vim.eval("setbufvar(bufnr(), 'remote', 'remote')")
            return bufnr
        bufnr = vim.eval(f"bufnr('{bufname}')")
        if bufnr == "-1" or force : 
            if self.is_remote(): 
                content = FileSystem().fetch(filepath)
                bufnr = do_open(content)
            else: 
                bufnr = vim.eval(f'bufadd("{filepath}")')
                vim.command(f"noswapfile call bufload('{filepath}')")
            return bufnr
        else: 
            return bufnr

    def bufexist(self, file):
        if not IsBufferExist(file): return False
        if vim.eval(f"getbufvar('{file}', 'remote', '')") == '': 
            return not self._is_remote
        else: 
            return self._is_remote

    def list_dir(self, dirpath):
        return rpc_wait("remotefs.list_dir", dirpath)

    def cd(self, dirpath):
        self.cwd = dirpath

    def glob(self, dirpath, pattern):
        pass

    def tree(self, dirpath=None):
        # return format:
        # DIR = {'files': [], 'dirs': DIR}
        if not hasattr(self, "cached_tree"):
            if not dirpath:
                dirpath = self.cwd
            results = rpc_wait("remotefs.tree", dirpath)
            self.cached_tree = DirectoryTree.from_dict(dirpath, results)
        return self.cached_tree

    def create_node(self, filepath):
        if filepath[-1] == '/': command = "mkdir"
        else: command = "touch"
        del self.cached_tree
        return self.command(f"{command} {filepath}")

    def remove_node(self, filepath):
        del self.cached_tree
        return self.command(f"rm -r {filepath}")
        

    def completer(self, cur_input):
        pass

    def exists(self, filepath):
        """ whether this file exist in remote filesystem.
        """
        return rpc_wait("remotefs.exists", filepath)

    def edit(self, filepath, force=False): 
        filepath = self.abspath(filepath)
        bufnr = FileSystem().bufload_file(filepath, force)
        GoToBuffer(bufnr, '.')

    def jumpto(self, location, method):
        GoToLocation(location, method)

    def command(self, command_str):
        try: 
            self.eval(command_str)
            return True
        except Exception as e: 
            print (f"Error while execute: {command_str}, {e}")
            return False
            

    def getcwd(self):
        return self.cwd

    def eval(self, command_str): 
        """ call bash command and get output """
        cwd = self.getcwd()
        command_str = f"cd {cwd} && " + command_str
        ret = rpc_wait("remotefs.eval", command_str)
        if ret['status'] == "ok":
            return ret['output']
        if ret['status'] == "error":
            raise RuntimeError(f"Eval Failed: {command_str} with error: {ret['error']}")

    def current_filepath(self):
        return self.filepath(vim.eval("bufname()"))
