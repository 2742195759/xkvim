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
from .windows import GlobalPreviewWindow, PreviewWindow
import time
from .log import debug, log
from urllib.parse import quote, unquote
from . import remote_fs
from .rpc import RPCServer, RPCChannel
from .remote_fs import FileSystem
from .buf_app_filetree import CursorLineBuffer
from .buf_app import Buffer
from .buf_app import WidgetBufferWithInputs, WidgetList, TextWidget, SimpleInput, WidgetBuffer, BufferHistory

class InsertCompleteBuffer(CursorLineBuffer):
    def __init__(self):
        self.max_height = 20
        self.win_options = {
            'maxwidth': 50,
            'maxheight': self.max_height,
            'filter': None,
            'pos': 'topleft',
            'line': "cursor+1",
            'col': "cursor",
            'posinvert': 1,
            'flip': 1,
            'zindex': 100,
            'padding': [0, 0, 0, 0],
            'border': [0, 0, 0, 0],
            'scrollbar': 1,
        }
        super().__init__(WidgetList("xxx", []), "insert_complete", "", None, self.win_options)
        self.items = []

    def set_complete_items(self, items):
        self.items = items
        self.redraw()

    def show(self): # no content, we hide the window.
        super().show()
        if len(self.items) == 0:    
            self.hide()
            return

    def make_table(self, items):
        if len(items) == 0: 
            return []
        table = [ 
            [ 
                i.get('abbr', i['word']), 
                i.get('menu', ""), 
                i['kind'],
            ] 
        for i in items ]
        return vim_utils.print_table(table)

    def onredraw(self):
        table = self.make_table(self.items)
        self._clear()
        self._put_strings(table)

class State: 
    def __init__(self, body):
        self.body = body
        self.mapping = []

    def save_and_remove_mapping(self, list_of_map):
        for item in list_of_map:
            saved = vim.eval(f'maparg("{item[0]}", "{item[1]}", 0, 1)')
            self.mapping.append((item[0], item[1], saved))
            if saved != {}: 
                is_buffer = ""
                if saved.get("buffer", '0') == '1': 
                    is_buffer = "<buffer>" 
                vim.command(f"{item[1]}unmap {is_buffer} {item[0]}")
            
    def restore_mapping(self):
        for left, mode, item in self.mapping: 
            # must exist
            #print ("unmap: ", left)
            vim.command(f"{mode}unmap <buffer> {left}")
            if item != {}: 
                with vim_utils.VimVariableGuard(item) as obj:
                    vim.eval(f'mapset("{mode}", 0, {obj})')

    def enter(self):
        raise NotImplementedError("not implement.")

    def process(self, cmd):
        raise NotImplementedError("not implement.")
    
    def exit(self):
        raise NotImplementedError("not implement.")

    def clear_auto(self):
        vim_utils.commands("""
            augroup InsertComplete
                autocmd!
            augroup END
        """)

class CloseState(State):
    def enter(self):
        self.body.hide()
        self.body.set_complete_items([])

    def exit(self):
        pass


class TypingState(State):
    def __init__(self, body, start_point, select_fn, done_fn): 
        super().__init__(body)
        self.start_point = start_point # 1-based
        self.select_fn = select_fn
        self.done_fn = done_fn
        self.trigger_point = vim_utils.GetCursorXY()[1] # 1-based
        self.origin_item = self.body.buf.items

    def close_typing_state(self):
        self.body.goto_state(CloseState(self.body))

    def enter(self):
        self.body.show(self.start_point)
        self.fire_item_select()
        keymap_register_commands = ("""
        inoremap <buffer> <C-n> <Cmd>py3 Xiongkun.InsertWindow().state.next()<cr>
        inoremap <buffer> <C-p> <Cmd>py3 Xiongkun.InsertWindow().state.previous()<cr>
        inoremap <buffer> <C-j> <Cmd>py3 Xiongkun.InsertWindow().state.next()<cr>
        inoremap <buffer> <C-k> <Cmd>py3 Xiongkun.InsertWindow().state.previous()<cr>
        inoremap <buffer> <up> <Cmd>py3 Xiongkun.InsertWindow().state.previous()<cr>
        inoremap <buffer> <down> <Cmd>py3 Xiongkun.InsertWindow().state.next()<cr>
        inoremap <buffer> <enter> <Cmd>py3 Xiongkun.InsertWindow().state.type_enter()<cr>
        inoremap <buffer> <bs> <Cmd>py3 Xiongkun.InsertWindow().state.type_backspace()<cr>
        inoremap <buffer> <C-w> <Cmd>py3 Xiongkun.InsertWindow().state.delete_word()<cr>
        inoremap <buffer> <space> <Cmd>py3 Xiongkun.InsertWindow().state.type_space()<cr>
        inoremap <buffer> . <Cmd>py3 Xiongkun.InsertWindow().state.type_dot()<cr>
        inoremap <buffer> <C-u> <Cmd>py3 Xiongkun.InsertWindow().state.delete_all()<cr>
        inoremap <buffer> <C-l> <Cmd>py3 Xiongkun.InsertWindow().state.stop()<cr>
        """)
        for exit_key in ['<c-x>', '<c-v>', '<c-z>']:
            exit_command = """inoremap <buffer> {exit_key} <Cmd>py3 Xiongkun.InsertWindow().state.stop('{exit_key_text}')<cr>\n"""
            keymap_register_commands += (exit_command.format(exit_key=exit_key, exit_key_text=exit_key.replace("<", "@")))
        # get all registered keys
        registered_keys = []
        for line in keymap_register_commands.split("\n"): 
            if line.strip():
                registered_keys.append([line.strip().split(" ")[2], 'i'])
        # restore old mapping
        self.save_and_remove_mapping(registered_keys)
        # register new mapping
        vim_utils.commands(keymap_register_commands)
        vim_utils.commands("""
        augroup InsertComplete
            autocmd!
            autocmd InsertLeave * py3 Xiongkun.InsertWindow().goto_state(Xiongkun.CloseState(Xiongkun.InsertWindow()))
            autocmd TextChangedI * py3 Xiongkun.InsertWindow().state.insert()
        augroup END
        """)

    def select_string(self):
        select_nr = self.body.buf.cur_cursor_line()
        if select_nr >= len(self.body.buf.items): 
            return ""
        cur_item = self.body.buf.items[select_nr]
        cur_col = vim_utils.GetCursorXY()[1] - 1 # 1-base -> 0-base
        backspace_num = cur_col - self.start_point + 1
        return "\x08"*backspace_num + cur_item['word']

    def stop(self, append_key=None):
        self.body.close()
        if append_key is not None: 
            append_key = append_key.replace("@", "<")
            if append_key.startswith("<"): append_key = "\\" + append_key
            vim.eval(f'feedkeys("{append_key}", "t")')
            

    def type_enter(self):
        ret = self.select_string()
        self.close_typing_state()
        with vim_utils.VimVariableGuard(ret) as obj:
            vim.eval(f'feedkeys({obj}, "in")')

        # close the next autocommand trigger. 
        vim.command("set ei=TextChangedI")
        vim.eval(f'feedkeys("\\<Ignore>", "n")') # start a next loop.
        vim.command("set ei=")

    def type_backspace(self):
        cur_col = vim_utils.GetCursorXY()[1] # 1-based
        if cur_col <= self.trigger_point: 
            self.close_typing_state()
        return vim.eval('feedkeys("\x08", "in")')

    def type_dot(self):
        self.close_typing_state()
        return vim.eval('feedkeys(".", "in")')

    def type_space(self):
        self.close_typing_state()
        return vim.eval('feedkeys(" ", "in")')

    def delete_word(self):
        self.close_typing_state()
        return vim.eval('feedkeys("\x17", "in")')

    def delete_all(self):
        self.close_typing_state()
        return vim.eval('feedkeys("\x15", "in")')

    def check_exit(self, word):
        for char in "()[]{}@#*": 
            if char in word: 
                self.close_typing_state()
                return True
        return False

    def insert(self):
        def fuzzy_filter(word, items):
            from fuzzyfinder import fuzzyfinder
            mapping = { id(item['word']):item for item in items }
            filtered_items = fuzzyfinder(word, [item['word'] for item in items])
            return [ mapping[id(item)] for item in filtered_items ]

        line = vim_utils.GetCurrentLine()
        cur_col = vim_utils.GetCursorXY()[1]
        col = self.start_point
        word = line[col-1:cur_col-1] # | start - end | cursor
        if self.check_exit(word):
            return
        items = fuzzy_filter(word, self.origin_item)
        self.body.buf.set_complete_items(items)
        self.fire_item_select()

    def next(self):
        self.body.buf.on_cursor_move('j')
        self.fire_item_select()

    def previous(self): 
        self.body.buf.on_cursor_move('k')
        self.fire_item_select()

    def fire_item_select(self):
        cur_item = self.body.current_item()
        if self.select_fn:
            self.select_fn(cur_item, vim.eval(f"popup_getpos({self.body.wid})"))

    def exit(self):
        self.clear_auto()
        self.restore_mapping()
        if self.done_fn:
            self.done_fn(None)

@vim_utils.Singleton
class InsertWindow:
    def __init__(self):
        self.state = None
        self.reset()

    def reset(self):
        self.buf = InsertCompleteBuffer()
        self.buf.create()
        self.buf.show()
        self.buf.hide()
        self.close()

    @property
    def wid(self):
        # get self.buf.wid
        # when deleted we will create a new one automatically.
        if not hasattr(self.buf, 'wid') or vim.eval(f"popup_getpos({self.buf.wid})") == {}: 
            self.reset()
        return self.buf.wid

    #@interface
    def complete(self, items, start_point, complete_change=None, complete_done=None):
        self.set_complete_items(items)
        self.goto_state(TypingState(self, start_point, complete_change, complete_done))

    def is_ready(self):
        return isinstance(self.state, CloseState)

    def goto_state(self, state):
        if self.state: 
            self.state.exit()
        self.state = state
        self.state.enter()

    def show(self, col):
        if self.buf._popup_closed_unexpected():
            self.reset()
        self.buf.show() # show first, we can create the window.
        self.move_to_cursor(col) # after create window, we can move it.

    def close(self):
        self.goto_state(CloseState(self))

    def current_item(self):
        buf : Buffer = self.buf
        if len(buf.items) == 0: return None
        select_nr = buf.cur_cursor_line()
        return buf.items[select_nr]

    def hide(self):
        if self.buf._popup_closed_unexpected():
            self.reset()
        self.buf.hide()

    def set_complete_items(self, items):
        if self.buf._popup_closed_unexpected():
            self.reset()
        self.buf.set_complete_items(items)

    def move_to_cursor(self, col):
        col_offset = vim_utils.GetCursorXY()[1] - col
        width, height = vim_utils.TotalWidthHeight()
        screen_line, screen_col = vim_utils.GetCursorScreenXY()                                                  
        if screen_line + self.buf.max_height >= height - 2: # out of screen - 2
           options = {
              'line':'cursor-1',
              'col':'cursor-'+str(col_offset), 
              'posinvert': False,
              'pos': 'botleft'
           }
        else: 
           options = {
              'line':'cursor+1',
              'col':'cursor-'+str(col_offset), 
              'posinvert': False,
              'pos': 'topleft'
           }
        self.buf.move_to(options)
