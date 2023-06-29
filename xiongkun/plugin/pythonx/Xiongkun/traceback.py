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
from .vim_utils import SetQuickFixList, vimcommand, FindWindowInCurrentTabIf
import os.path as osp
from . import remote_fs 

file_pattern = r"[a-zA-Z0-9/\._-]+"
number_pattern = r"[0-9]+"

@vim_register(command="Traceback")
def AnalysisTraceback(args):
    word = vim_utils.GetVisualWords()
    lines = word.split("\n")
    locs = []
    for line, code in zip(lines, lines[1:]):
        line = line.strip()
        code = code.strip()
        if line.startswith("File \""): 
            result = re.search(r'File "(.+)", line (.+), in (.+)', line)
            filename, lineno, name = result.groups()
            if osp.exists(filename): 
                locs.append(remote_fs.Location(filename, int(lineno)))
    def prediction(wnr):
        return vim.eval(f"getwinvar({wnr}, '&buftype')") == "terminal"
    bufnr = int(FindWindowInCurrentTabIf(prediction))
    if int(vim.eval("bufnr()")) != bufnr: 
        SetQuickFixList(locs, jump='last')

@vim_register(keymap="<space>gf", command="TracebackLine")
def TracebackOneLine(args):
    """ 
    `TracebackLine`: goto the error line and quick fix bugs, auto parse the filename
    >>> TracebackLine
    --------------------
    + remote
    + key = n: <space> gf
    """
    line = vim_utils.GetCurrentLine().strip()
    patterns = [
        f"({file_pattern}):({number_pattern})", 
        f'File "({file_pattern})", line ({number_pattern}), in',
        f"({file_pattern})\\(({number_pattern})\\)",
        f'file "({file_pattern})", line ({number_pattern})', # pycode error line.
    ]
    log (patterns)
    loc = None
    for patt in patterns:
        result = re.search(patt, line)
        if result is None: 
            continue
        filename, lineno = result.groups()
        if remote_fs.FileSystem().exists(filename): 
            loc = remote_fs.Location(filename, int(lineno))
        else: 
            print ("trace back file not exists: ", filename)
    if loc is None: 
        print ("Non't a valid python traceback line.")
        return 
    remote_fs.GoToLocation(loc, ".")

