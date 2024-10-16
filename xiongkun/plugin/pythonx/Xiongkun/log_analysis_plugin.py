import vim
import subprocess
import os
from os import path as osp
from . import vim_utils
from .func_register import *
import random
import threading
import json
from contextlib import contextmanager
import time
import os.path as osp
from .log import log, log_google
from urllib.parse import quote

"""
there is a log of command defined in there to analysis logs and bug info.
Specially for paddle.

1. Op Count
2. Auto Log split and diff in windows.
"""

@vim_register(command="RegDiff", with_args=True)
def RegDiff(args):
    """
    open windows and diff 2 registers
    """
    if len(args) < 2: 
        print ("Please Input 2+ register name. such as: RegDiff a b / RegDiff a b c")
        return
    for i, r in enumerate(args): 
        if i == 0: 
            vim_utils.commands("tabe")
        else: 
            vim_utils.commands("botright vnew")
        vim_utils.commands("put " + r)
        vim_utils.commands("diffthis")

@vim_register(command="LogSplit", with_args=True)
def LogSplit(args):
    """
    Split file with Start and End marker and store the info into registers from `qwer` to `tyuiop`
    """
    all_args = " ".join(args)
    if len(all_args.split('/')) != 2: 
        print ("Please Input 2 line spliter, split with `/`. such as: LogSplit Start Step/End Step")
        return
    start, end = all_args.split("/")
    starts = []
    ends = []
    texts = vim_utils.GetAllLines()
    for idx, line in enumerate(texts):
        if start in line:
            starts.append(idx)
        if end in line:
            ends.append(idx)
    assert len(starts) == len(ends)
    register_name = "qwertyuiop"
    for idx, (s, e) in enumerate(zip(starts, ends)):
        if s == e: 
            e = starts[idx+1] if idx + 1 < len(starts) else 1000000
        vim_utils.commands("redir @" + register_name[idx])
        print ("\n".join(texts[s:e+1]))
        vim_utils.commands("redir END")

@vim_register(command="LogSum", with_args=True)
def LogSum(args):
    """
    Sum Log column
    """
    column = args[0]
    awk = "%!awk '{sum+=$%d} END {print sum}'" % int(column)
    vim.command(awk)

@vim_register(command="LogSort", with_args=True)
def LogSort(args):
    """
    Sort Log column
    """
    key = int(args[0])
    cmd = "sort -k %d -n" % key
    vim.command(cmd)
