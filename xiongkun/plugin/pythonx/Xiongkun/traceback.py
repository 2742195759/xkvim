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
from .vim_utils import Location, SetQuickFixList, vimcommand, FindWindowInCurrentTabIf
import os.path as osp

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
                locs.append(Location(filename, int(lineno)))
    def prediction(wnr):
        return vim.eval(f"getwinvar({wnr}, '&buftype')") == "terminal"
    bufnr = int(FindWindowInCurrentTabIf(prediction))
    if int(vim.eval("bufnr()")) != bufnr: 
        SetQuickFixList(locs, jump='last')

@vim_register(keymap="<space>gf", command="TracebackLine")
def AnalysisTraceback(args):
    line = vim_utils.GetCurrentLine().strip()
    loc = None
    if line.startswith("File \""): 
        result = re.search(r'File "(.+)", line (.+), in (.+)', line)
        filename, lineno, name = result.groups()
        if osp.exists(filename): 
            #filename = filename.replace("build/", "")
            loc = (Location(filename, int(lineno)))
    if loc is None: 
        print ("Non't a valid python traceback line.")
        return 
    vim_utils.GoToLocation(loc, "t")
