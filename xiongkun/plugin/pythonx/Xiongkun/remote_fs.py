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
from .rpc import rpc_call, rpc_wait
from .vim_utils import vimcommand
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
        # TODO: 
        return filepath

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
                vim.command(f"b {bufnr}")
                vim.command(f"setlocal noswapfile")
                vim.command(f"read {tmp_file}")
                vim.command("normal ggdd")
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
                vim.eval(f"bufload('{filepath}')")
            return bufnr
        else: 
            return bufnr

    def list_dir(self, dirpath):
        return rpc_wait("remotefs.list_dir", dirpath)

    def cd(self, dirpath):
        self.cwd = dirpath

    def glob(self, dirpath, pattern):
        pass

    def tree(self, dirpath=None):
        # return format:
        # DIR = {'files': [], 'dirs': DIR}
        if not dirpath:
            dirpath = self.cwd
        results = rpc_wait("remotefs.tree", dirpath)
        return results

    def mkdir(self, dirpath):
        pass

    def touch(self, filepath):
        pass

    def completer(self, cur_input):
        pass

    def exists(self, filepath):
        """ whether this file exist in remote filesystem.
        """
        return rpc_wait("remotefs.exists", filepath)

    def edit(self, filepath, force=False): 
        bufnr = FileSystem().bufload_file(filepath, force)
        GoToBuffer(bufnr, '.')

    def jumpto(self, location, method):
        GoToLocation(location, method)

    def command(self, command_str):
        ret = rpc_wait("remotefs.command", command_str)
        if ret == 0:
            return True
        else: 
            print (f"Command Failed: {command_str} with code {ret}")
            return False

    def current_filepath(self):
        return self.filepath(vim.eval("bufname()"))
