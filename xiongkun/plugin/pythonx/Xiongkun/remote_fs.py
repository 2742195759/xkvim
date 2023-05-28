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

remote_prefix = "remote://"

def _to_remote(file):
    return remote_prefix+file

def get_directory():
    from .rpc import remote_project
    if remote_project is None: 
        return vim.eval("getcwd()")
    else: 
        return _to_remote(remote_project.root_directory)

def get_base(file):
    if not is_remote(file): return file
    return file.split("remote://")[1]

def to_remote(file):
    root_directory = get_base(get_directory())
    assert is_remote(file) is False
    if not file.startswith("/"):
        file = osp.join(root_directory, file)
    return _to_remote(file)

def to_url(file):
    if is_remote_mode():return to_remote(file)
    else: return file

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
    msg = rpc_wait("remotefs.store", filepath, "\n".join(lines))
    if msg != "success.": 
        vim.command(f"echom '{msg}'")
        vim.command("set modified")

def LoadBuffer(url):
    bufnr = vim.eval(f"bufnr('{url}')")
    def do_open(content): 
        tmp_file = vim_utils.TmpName()
        with open(tmp_file, "w") as f: 
            f.write(content)
        bufnr = vim.eval(f'bufadd("{url}")')
        with vim_utils.CurrentBufferGuard():
            vim.command(f"b {bufnr}")
            vim.command(f"read {tmp_file}")
            vim.command("normal ggdd")
            vim.command("set nomodified")
        return bufnr
    if bufnr == "-1": 
        if is_remote(url): 
            filepath = get_base(url)
            content = rpc_wait("remotefs.fetch", filepath)
            bufnr = do_open(content)
        else: 
            bufnr = vim.eval(f'bufadd("{url}")')
            vim.eval(f"bufload('{url}')")
        return bufnr
    else: 
        return bufnr

@vim_register(command="RemoteEdit", with_args=True)
def RemoteEdit(args):
    url = args[0]
    filepath = get_base(url)
    bufnr = LoadBuffer(url)
    GoToBuffer(bufnr, 'e')
            
vim_utils.commands(""" 
augroup RemoteWrite
    autocmd!
    autocmd BufWriteCmd remote://* RemoteSave
augroup END
    """)


"""
text access and modification function.
"""
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
    if is_remote_mode():
        location = location.to_remote()
    bufnr = LoadBuffer(location.full_path)
    GoToBuffer(bufnr, method)
    vimcommand(f":{location.getline()}")
    if location.getcol() != 1:
        vimcommand("normal %d|"%(location.getcol()))
    vimcommand("normal zv")

class Location: 
    def __init__(self, file, line=1, col=1, base=1):
        if isinstance(file, int): 
            file = vim.eval(f"bufname({file})")
        self.full_path = file
        if not is_remote(file): 
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
        return Location(
            to_remote(self.full_path),
            self.line, 
            self.col, 
            self.base
        )

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


@vim_register(command="GotoFile", keymap="gf")
def GotoFile(args):
    if is_remote(vim.eval("bufname()")): 
        url = to_remote(vim.eval('expand("<cfile>")'))
        bufnr = LoadBuffer(url)
        GoToBuffer(bufnr, ".")
    else: 
        vim.command("normal! gf") # normal mode
