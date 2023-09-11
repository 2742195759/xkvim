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
from .vim_utils import VimWindow, Singleton, VimKeyToChar, CursorGuard, get_char_no_throw

""" 
QuickJump is not in a prefect state.

TODO:(xiongkun)
1. Vim 如果全部使用 Python 对 UI 非常不友好。因此我们需要一个机制来进行序列化编程，将不同的函数
装载入不同的 VimFunction 中进行执行，同时在Vim的Function之间自动插入 redraw! 来实现强制刷新
UI。

2. 有汉字，其他字符，Unicode等，会扰乱了 col 的坐标。
3. 统一搜索，将 S 作为统一的搜索语言。可以在window之间进行跳转，如果是S，那么需要输入2个字符。s 输入一个字符。 
    - OK
4. [optional] optimizer the all_labels.
5. long line will have error label popup windows.

"""

#all_labels = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890;'.,/@!#$%^&*()<>{}+-="
all_labels = "asdfjkl;ghqwertpoiuyzxcvmnbABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'.,/@!#$%^&*()<>{}+-="
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
        #log("[InnerWindow]: screen pos: ", screen_pos)
        item = JumpItem(screen_pos, onjump, callback)
        item.bufpos = buffer_pos
        return item

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

def get_pattern(char_num):
    """
    cmd = 's' | 'S'
    """
    try:
        pattern = []
        for i in range(char_num):
            pattern.append(get_char_no_throw())
        pattern = "".join(pattern)
        pattern = vim_utils.escape(pattern, '()[]|\\?+.*')
        return pattern
    except:
        return None

def search_in_window(pattern, wid):
    lines = vim_utils.GetAllLines(vim_utils.VimWindow(wid).bufnr)
    top, bot = vim_utils.VimWindow(wid).display_rows
    searched = [] # JumpItem
    last_is_fold=False
    for linenr, line in enumerate(lines): 
        if linenr >= top-1 and linenr <= bot-1: 
            if vim_utils.isLineFolded(linenr+1):  
                if last_is_fold: continue
                else: 
                    last_is_fold = True
                    bufpos = (linenr+1, 1)
                    if VimWindow(wid).in_window_view(*bufpos): 
                        searched.append(JumpItem.from_buffer_pos(bufpos, wid, None))
            else: 
                last_is_fold = False
                for f in re.finditer(pattern, line.lower()):#, overlapped=True): 
                    bufpos = (linenr+1, f.span()[0]+1)
                    if VimWindow(wid).in_window_view(*bufpos): 
                        searched.append(JumpItem.from_buffer_pos(bufpos, wid, None))
    return searched

def inner_window_lines(wid, on_select):
    lines = vim_utils.GetAllLines(vim_utils.VimWindow(wid).bufnr)
    top, bot = vim_utils.VimWindow(wid).display_rows
    searched = [] # JumpItem
    for linenr, line in enumerate(lines): 
        if linenr >= top-1 and linenr <= bot-1: 
            bufpos = (linenr+1, 1)
            if VimWindow(wid).in_window_view(*bufpos): 
                searched.append(JumpItem.from_buffer_pos(bufpos, wid, on_select))
    return searched

def interactive_buffer_jump(keys, search_fn): 
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
            return True
        else: 
            print("reach end, exit.")
            return False

    def clear_last():
        ### recover
        recover_buffer(searched)
        for m in matches:
            m.delete()
    # max item is support for len(all_labels)
    yield "redraw"
    inp = None
    if keys > 0: 
        inp = get_pattern(keys)
        if inp is None: 
            return 
    searched = search_fn(inp)
    label_map, matches = redraw(searched)
    if len(searched) == 0: 
        print("not found!")
        return 
    while True: 
        yield "redraw"
        c = get_char_no_throw()
        if c == ' ': 
            if not next_page(): 
                break
        else: 
            jump_procedure(c)
            break

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
        #log("[Redraw Popup]: ", screen_row, screen_col, label)
        popups.append(vim_utils.TextPopup(label, screen_row, screen_col, highlight="CtrlPwhite", z_index=300))
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

@vim_register(command="BufferJump", with_args=True, interactive=True)
def BufferJump(args):
    ## search all the matches
    vim_utils.WindowView.clear()
    def search_fn(pattern):
        return search_in_window(pattern, VimWindow().id)
    from .ijump import DFAContext
    DFAContext().set_dfa(interactive_buffer_jump(1, search_fn))

#@vim_register(command="JumpInnerWindow", with_args=True, interactive=True)
def JumpLines(args):
    ## search all the matches
    vim_utils.WindowView.clear()
    win_id = int(args[0])
    def default_select(item):
        print("Select", item.bufpos[0])
    on_select = default_select
    if len(args) >= 2: 
        on_select = args[1]
    def search_fn(pattern):
        searched = inner_window_lines(win_id, on_select)
        for search in searched: 
            screen_pos = search.screen_pos
            search.screen_pos = screen_pos[0]+1, screen_pos[1]+2
        searched = searched[:-1]
        return searched

    from .ijump import DFAContext
    DFAContext().set_dfa(interactive_buffer_jump(0, search_fn))
    vim.command("call InteractDo()")

@vim_register(command="WindowJump", with_args=True, interactive=True)
def WindowJump(args):
    vim_utils.WindowView.clear()
    def search_fn(pattern):
        searched = [] # lineno, startpos, endpos: [startpos, endpos)
        for win_id in vim_utils.IteratorWindowCurrentTab():
            searched.append(JumpItem.from_window_display_pos((1,1), win_id, None))
        return searched 
    from .ijump import DFAContext
    DFAContext().set_dfa(interactive_buffer_jump(0, search_fn))

@vim_register(command="GlobalJump", with_args=True, interactive=True)
def GlobalJump(args):
    ## search all the matches

    from .ijump import DFAContext
    def search_fn(pattern):
        searched = []
        vim_utils.WindowView.clear()
        for win_id in vim_utils.IteratorWindowCurrentTab():
            searched.extend(search_in_window(pattern, win_id))
        return searched 
    DFAContext().set_dfa(interactive_buffer_jump(2, search_fn))

@vim_register(command="QuickPeek", with_args=True)
def QuickPeek(args):
    ## search all the matches
    with CursorGuard():
        vim.command("BufferJump")
        vim.command('execute "normal \\<m-p>"')

@Singleton
class GlobalInsertStack: 
    def __init__(self):
        self.cur = 0
        self.max_size = 100
        self.stack = []

    def jump_previous(self):
        if self.cur <= 0: return 
        self.cur -= 1
        pos = self.stack[self.cur]
        with vim_utils.VimVariableGuard(pos) as pos:
            vim.eval(f'setpos(".", {pos})')

    def push(self):
        assert self.cur >= 0
        if len(self.stack) > self.max_size: 
            self.stack.pop(0)
        pos = vim.eval("getpos('.')")
        self.stack.append(pos)
        self.cur = len(self.stack)

vim_utils.commands(
"""
augroup QuickJumpInsert
    autocmd InsertLeave * py3 Xiongkun.GlobalInsertStack().push()
augroup END
"""
)

@vim_register(keymap="ge")
def JumpLastEdit(args):
    GlobalInsertStack().jump_previous()

@vim_register(keymap="gl")
def JumpLastBuffer(args):
    vim.eval('feedkeys("\\<c-^>", "ix")')
