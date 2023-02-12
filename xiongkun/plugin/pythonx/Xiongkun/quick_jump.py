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
from .vim_utils import VimWindow


""" 
QuickJump is not in a prefect state.

TODO:(xiongkun)
1. Vim 如果全部使用 Python 对 UI 非常不友好。因此我们需要一个机制来进行序列化编程，将不同的函数
装载入不同的 VimFunction 中进行执行，同时在Vim的Function之间自动插入 redraw! 来实现强制刷新
UI。
主要目的，不希望将 State 这类全局变量暴露给不同的脚本。统一流程。

2. 有汉字，其他字符，Unicode等，会扰乱了 col 的坐标。
3. 统一搜索，将 S 作为统一的搜索语言。可以在window之间进行跳转，如果是S，那么需要输入2个字符。s 输入一个字符。 
4. [optional] optimizer the all_labels.

"""

all_labels = "abcdefghijklmnopgrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890;'.,/@!#$%^&*()<>{}+-="
"""
    fontend_type: 
        - 'popup': use popup-window to show labels, slow but unified.
        - 'buffer': use buffer to show labels, quick but limited. [deprecated, may have bugs, code is just for fun.]
"""
fontend_type = "popup"


class JumpItem:
    def __init__(self, screen_pos, onjump, callback):
        """
        parameters:
        """
        self.screen_pos = screen_pos
        self.callback = callback
        #self.buffer_pos = buffer_pos
        self.jump = onjump

    @classmethod
    def from_buffer_pos(cls, buffer_pos, winid, onjump=None, callback=None):
        """ 
        buffer_pos: 1-based buffer_pos.
        winid     : None for current window, id for win_id.
        callback  : a callback fn called after jump.
        """
        winid = winid
        if winid is None: 
            winid = vim_utils.VimWindow().id
        def buffer_jump(self): 
            vim.eval(f'win_gotoid({winid})')
            vim_utils.SetCursorXY(buffer_pos[0], buffer_pos[1])
        if onjump is None: 
            onjump = buffer_jump
        screen_pos = vim_utils.VimWindow(winid).to_screen_pos(buffer_pos[0], buffer_pos[1])
        return JumpItem(screen_pos, onjump, callback)

    @classmethod
    def from_window_display_pos(cls, window_pos, winid, callback):
        """ 1-based window_pos
        """
        winid = winid
        if winid is None: 
            winid = vim_utils.VimWindow().id
        def window_jump(self): 
            vim.eval(f'win_gotoid({winid})')
        display_pos = vim_utils.VimWindow(winid).display_rows
        buffer_pos = display_pos[0] + window_pos[0] - 1, window_pos[1]
        return cls.from_buffer_pos(buffer_pos, winid, window_jump, callback)

    @classmethod
    def from_window_cursor(cls, winid, callback):
        winid = winid
        if winid is None: 
            winid = vim_utils.VimWindow().id
        def window_jump(self): 
            vim.eval(f'win_gotoid({winid})')
        display_pos = vim_utils.VimWindow(winid).display_rows
        buffer_pos = display_pos[0] + window_pos[0] - 1, window_pos[1]
        return cls.from_buffer_pos(buffer_pos, winid, window_jump, callback)

    @classmethod
    def from_screen_pos(cls, buffer_pos, winid, callback):
        assert False

    def on_select(self):
        self.jump(self)
        if self.callback is not None: 
            self.callback()

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

def get_pattern(char_num):
    """
    cmd = 's' | 'S'
    """
    try:
        pattern = []
        for i in range(char_num):
            pattern.append(chr(int(vim.eval("getchar()"))))
        pattern = "".join(pattern)
        pattern = vim_utils.escape(pattern, '()[]|\\?+.*')
        return pattern
    except:
        return None

def search_in_window(pattern, wid):
    lines = vim_utils.GetAllLines(vim_utils.VimWindow(wid).bufnr)
    log("Buffer:", lines)
    top, bot = vim_utils.VimWindow(wid).display_rows
    searched = [] # JumpItem
    for linenr, line in enumerate(lines): 
        if linenr >= top-1 and linenr <= bot-1: 
            for f in re.finditer(pattern, line.lower()):#, overlapped=True): 
                searched.append(JumpItem.from_buffer_pos((linenr+1, f.span()[0]+1), wid, None))
    return searched

@vim_register(command="BufferJump", with_args=True)
def BufferJump(args):
    ## search all the matches
    pattern = get_pattern(1)
    if pattern is None: return
    searched = search_in_window(pattern, VimWindow().id)
    JumpStart(searched)


@vim_register(command="WindowJump", with_args=True)
def WindowJump(args):
    searched = [] # lineno, startpos, endpos: [startpos, endpos)
    for win_id in vim_utils.IteratorWindowCurrentTab():
        #log("WindowIter:", win_id)
        searched.append(JumpItem.from_window_display_pos( (1,1), win_id, None))
        #searched.append(JumpItem.from_window_display_pos(
            #vim_utils.GetCursorXY(win_id), win_id, None))
    JumpStart(searched)


@vim_register(command="GlobalJump", with_args=True)
def GlobalJump(args):
    ## search all the matches
    pattern = get_pattern(2)
    if pattern is None: return
    searched = []
    for win_id in vim_utils.IteratorWindowCurrentTab():
        log(win_id)
        searched.extend(search_in_window(pattern, win_id))
    JumpStart(searched)


def JumpStart(searched):
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
            item = searched[label_map[c]] # x, y
            item.on_select()

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
        screen_row, screen_col = item.screen_pos
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
