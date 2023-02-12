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
QuickJump is not in a prefect state.

TODO:(xiongkun)
1. Vim 如果全部使用 Python 对 UI 非常不友好。因此我们需要一个机制来进行序列化编程，将不同的函数
装载入不同的 VimFunction 中进行执行，同时在Vim的Function之间自动插入 redraw! 来实现强制刷新
UI。
主要目的，不希望将 State 这类全局变量暴露给不同的脚本。统一流程。

2. 有汉字，其他字符，Unicode等，会扰乱了 col 的坐标。
3. 统一搜索，将 S 作为统一的搜索语言。可以在window之间进行跳转，如果是S，那么需要输入2个字符。s 输入一个字符。

"""

all_labels = "abcdefghijklmnopgrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890;'.,/@!#$%^&*()<>{}+-="
expected_char = 1
"""
    fontend_type: 
        - 'popup': use popup-window to show labels, slow but unified.
        - 'buffer': use buffer to show labels, quick but limited.
"""
fontend_type = "popup"

class State:
    jump_fn = None
    next_fn=None
    is_stop=1
    inputs=[]
    @classmethod
    def clear(cls):
        cls.inputs = []
        cls.is_stop=1
        cls.jump_fn=None
        cls.next_fn=None


@vim_register(command="QuickJump", with_args=False)
def QuickJump(args):
    try:
        c = chr(int(vim.eval("getchar()")))
    except:
        c = None
    if c == ' ': 
        State.next_fn()
    else: 
        State.jump_fn(c)
        State.clear()

def get_pattern(cmd):
    """
    cmd = 's' | 'S'
    """
    if cmd == 'S':
        """ Jump between all windows in current tabpage.
        """
        return State.last
    elif cmd == 's':
        """ Jump between current windows.
        """
        try:
            pattern = []
            for i in range(expected_char):
                pattern.append(chr(int(vim.eval("getchar()"))))
            pattern = "".join(pattern)
            pattern = vim_utils.escape(pattern, '()[]|\\?.*')
            return pattern
        except:
            return None
    return None

@vim_register(command="PreJump", with_args=True)
def PreJump(args):
    ## search all the matches
    assert args[0] in ['s', 'S']
    pattern = get_pattern(args[0])
    if pattern is None: return
    lines = vim_utils.GetAllLines()
    top, bot = vim_utils.VimWindow().display_lines
    searched = [] # lineno, startpos, endpos: [startpos, endpos)

    for linenr, line in enumerate(lines): 
        if linenr >= top-1 and linenr <= bot-1: 
            for f in re.finditer(pattern, line.lower()):#, overlapped=True): 
                searched.append((linenr, f.span()[0], f.span()[1]))

    # max item is support for len(all_labels)
    label_map, matches = redraw(searched)

    def clear_last():
        ### recover
        recover_buffer(searched)
        for m in matches:
            m.delete()

    # perform jump
    def jump_procedure(c):
        clear_last()
        ### jump
        if c in label_map: 
            to_jump = searched[label_map[c]] # x, y
            vim_utils.SetCursorXY(to_jump[0]+1, to_jump[1]+1)

    def next_page():
        nonlocal searched, matches, label_map
        clear_last()
        searched = searched[len(all_labels):]
        if len(searched) > 0:
            label_map, matches = redraw(searched)
            State.is_stop = 0
        else: 
            print("reach end, exit.")
            State.is_stop = 1

    State.jump_fn = jump_procedure
    State.next_fn = next_page
    if len(searched) > 0: 
        State.is_stop = 0
    else:
        print("not found!")
        State.is_stop = 1
        

def redraw(searched):
    if fontend_type == 'buffer':
        label_map, matches = redraw_buffer(searched)
    elif fontend_type == 'popup':
        label_map, matches = redraw_popup(searched)
    return label_map, matches

def redraw_popup(searched):
    searched = searched[:len(all_labels)]
    mapping = {}
    popups = []
    for idx, item in enumerate(searched):
        # muliply rewrite 
        linenr, startpos, endpos = item
        screen_row, screen_col = vim_utils.VimWindow().to_screen_pos(linenr+1, startpos+1)
        label = all_labels[idx]
        mapping[label] = idx
        popups.append(vim_utils.TextPopup(label, screen_row, screen_col, highlight="CtrlPwhite"))
    return mapping, popups


def redraw_buffer(searched):
    searched = searched[:len(all_labels)]
    mapping = {}
    matches = []
    for idx, item in enumerate(searched):
        # muliply rewrite 
        linenr, startpos, endpos = item
        label = all_labels[idx]
        mapping[label] = idx
        new_line = list(vim_utils.GetLine(linenr+1))
        new_line[startpos] = label
        vim_utils.SetLine(linenr+1, "".join(new_line))
        m = vim_utils.Matcher()
        m.match("CtrlPwhite", row_range=(linenr, linenr+2), col_range=(startpos, startpos+2))
        matches.append(m)
    return mapping, matches

def recover_buffer(searched):
    searched = searched[:len(all_labels)]
    if fontend_type == 'buffer' and len(searched) > 0: 
        with vim_utils.CursorGuard():
            # command u will change the cursor position.
            vim.command(':silent u')
