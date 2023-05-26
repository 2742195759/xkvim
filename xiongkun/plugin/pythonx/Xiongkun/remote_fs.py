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
from .rpc import rpc_call

remote_prefix = "remote://"

def get_base(file):
    if not is_remote(file): return file
    return file.split("remote://")[1]

def to_remote(file):
    return "remote://"+file

def is_remote(file):
    return "remote://" in file

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

        if vim.eval(f"bufnr('{url}')") == "-1": 
            rpc_call("remotefs.fetch", do_open, filepath)
        else: 
            vim.command(f"b {url}")
            
vim_utils.commands(""" 
augroup RemoteWrite
    autocmd!
    autocmd BufWriteCmd remote://* RemoteSave
augroup END
    """)
