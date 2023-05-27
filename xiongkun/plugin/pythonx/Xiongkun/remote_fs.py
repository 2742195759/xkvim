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
from .rpc import rpc_call
from .vim_utils import vimcommand
import os

remote_prefix = "remote://"

def get_directory():
    from .rpc import remote_project
    if remote_project is None: 
        return vim.eval("getcwd()")
    else: 
        return to_remote(remote_project.root_directory)

def get_base(file):
    if not is_remote(file): return file
    return file.split("remote://")[1]

def to_remote(file):
    return "remote://"+file

def is_remote(file):
    return "remote://" in file

def is_remote_mode():
    return is_remote(get_directory())

@vim_register(command="RemoteSave")
def RemoteSave(args):
    url = vim.eval("bufname()")
    filepath = get_base(url)
    bufnr = vim.eval(f"bufnr('{url}')")
    lines = vim.eval(f"getbufline({bufnr}, 1, '$')")
    vim.command("set nomodified")
    def do_open(msg): 
        if msg != "success.": 
            vim.command(f"echom '{msg}'")
            vim.command("set modified")
    rpc_call("remotefs.store", do_open, filepath, "\n".join(lines))
        

@vim_register(command="RemoteEdit", with_args=True)
def RemoteEdit(args):
    url = args[0]
    filepath = get_base(url)
    if not is_remote(url): vim.command(f"e {url}")
    else: 
        def do_open(content): 
            tmp_file = vim_utils.TmpName()
            with open(tmp_file, "w") as f: 
                f.write(content)
            bufnr = vim.eval(f'bufadd("{url}")')
            vim.command(f"b {bufnr}")
            vim.command(f"read {tmp_file}")
            vim.command("normal ggdd")
            vim.command("set nomodified")
        bufnr = vim.eval(f"bufnr('{url}')")
        if bufnr == "-1": 
            rpc_call("remotefs.fetch", do_open, filepath)
        else: 
            vim.command(f"b {bufnr}")
            
vim_utils.commands(""" 
augroup RemoteWrite
    autocmd!
    autocmd BufWriteCmd remote://* RemoteSave
augroup END
    """)

"""
text access and modification function.
"""

def GoToLocation(location, method):
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
    if is_remote_mode():
        location.to_remote()
        vim.command(f"RemoteEdit {location.full_path}")
        return 

    norm_methods = {
        'e': 'e!',
        '.': 'e!',
        'p': 'pedit!',
        't': 'tabe!',
        'v': 'vne!',
        's': 'split!',
        'b': 'b',
        'sb': 'vertical sb',
    }
    view_methods = {
        'e': 'noswapfile e',
        '.': 'noswapfile e',
        'p': 'noswapfile pedit',
        's': 'noswapfile split',
        't': 'noswapfile tabe',
        'v': 'noswapfile vne',
        'b': 'noswapfile b',
        'sb':'noswapfile vertical sb',
    }
    vim_method = norm_methods[method]
    if HasSwapFile(location.getfile()): 
        vim_method = view_methods[method]
    vimcommand("%s +%d %s"%(vim_method, location.getline(), location.getfile()))
    if location.getcol() != 1:
        vimcommand("normal %d|"%(location.getcol()))
    vimcommand("normal zv")

class Location: 
    def __init__(self, file, line=1, col=1, base=1):
        if isinstance(file, int): 
            file = vim.eval(f"bufname({file})")
        self.full_path = osp.abspath(file)
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

    def to_remote(self):
        self.full_path = to_remote(self.full_path)

class LocationRange:
    def __init__(self, start_loc, end_loc):
        self.start = start_loc
        self.end = end_loc
        assert (self.start.getfile() == self.end.getfile())

def HasSwapFile(path):
    abspath = os.path.abspath(path)
    basename = os.path.basename(abspath)
    pattern = os.path.dirname(abspath) + "/." + basename + ".*"
    import glob
    if len(glob.glob(pattern)): 
        return True
    return False

