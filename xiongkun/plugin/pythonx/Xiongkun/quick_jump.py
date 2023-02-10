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


"""
TODO:(xiongkun)
Vim 如果全部使用 Python 对 UI 非常不友好。因此我们需要一个机制来进行序列化编程，将不同的函数
装载入不同的 VimFunction 中进行执行，同时在Vim的Function之间自动插入 redraw! 来实现强制刷新
UI。

主要目的，不希望将 State 这类全局变量暴露给不同的脚本。统一流程。
"""

class State:
    caller = None
    pass

@vim_register(command="QuickJump", with_args=False)
def QuickJump(args):
    if State.caller: 
        State.caller()
    State.caller = None

@vim_register(command="PreJump", with_args=False)
def PreJump(args):
    try:
        a = chr(int(vim.eval("getchar()")))
        b = chr(int(vim.eval("getchar()")))
    except:
        return
    pattern = a + b
    ## search all the matches
    lines = vim_utils.GetAllLines()
    top, bot = vim_utils.VimWindows().display_lines
    searched = [] # lineno, startpos, endpos: [startpos, endpos)

    for linenr, line in enumerate(lines): 
        if linenr >= top and linenr <= bot: 
            for f in re.finditer(pattern, line.lower()):#, overlapped=True): 
                searched.append((linenr, f.span()[0], f.span()[1]))

    # max item is only support 26.
    searched = searched[:26]
    ## redraw all the labels, and return label map
    label_map, matches = redraw_buffer(searched)

    # perform jump
    def jump_procedure():
        try:
            c = chr(int(vim.eval("getchar()")))
        except:
            c = None
        ### recover
        recover_buffer(searched)
        for m in matches:
            m.delete()
        ### jump
        if c in label_map: 
            to_jump = searched[label_map[c]] # x, y
            vim_utils.SetCursorXY(to_jump[0]+1, to_jump[1]+1)

    State.caller = jump_procedure

def redraw_buffer(searched):
    mapping = {}
    matches = []
    for idx, item in enumerate(searched):
        # muliply rewrite 
        linenr, startpos, endpos = item
        label = chr(ord('a') + idx)
        mapping[label] = idx
        new_line = list(vim_utils.GetLine(linenr+1))
        new_line[startpos] = label
        vim_utils.SetLine(linenr+1, "".join(new_line))
        m = vim_utils.Matcher()
        m.match("Error", row_range=(linenr, linenr+2), col_range=(startpos, endpos))
        matches.append(m)
    return mapping, matches

def recover_buffer(searched):
    if len(searched) > 0: 
        vim.command('u')
