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
        self.win_options = {
            'maxwidth': 50,
            'maxheight': 30,
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
        if len(self.items) == 0:    
            self.hide()
            return
        super().show()

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
    def __init__(self, body, start_point): 
        super().__init__(body)
        self.start_point = start_point # 1-based

    def close_typing_state(self):
        self.body.goto_state(CloseState(self.body))

    def enter(self):
        print ("enter typing state")
        self.body.show(self.start_point)
        self.save_and_remove_mapping([
            ['<c-n>', 'i'],
            ['<c-p>', 'i'],
            ['<enter>', 'i'],
            ['<tab>', 'i'],
            ['<bs>', 'i'],
            ['<c-w>', 'i'],
            ['<c-u>', 'i'],
            ['<up>', 'i'],
            ['<down>', 'i'],
            ['<space>', 'i'],
            ['.', 'i'],
        ])
        vim_utils.commands("""
        inoremap <buffer> <C-n> <Cmd>py3 Xiongkun.InsertWindow().state.next()<cr>
        inoremap <buffer> <C-p> <Cmd>py3 Xiongkun.InsertWindow().state.previous()<cr>
        inoremap <buffer> <up> <Cmd>py3 Xiongkun.InsertWindow().state.previous()<cr>
        inoremap <buffer> <down> <Cmd>py3 Xiongkun.InsertWindow().state.previous()<cr>
        inoremap <buffer> <enter> <Cmd>py3 Xiongkun.InsertWindow().state.type_enter()<cr>
        inoremap <buffer> <tab> <Cmd>py3 Xiongkun.InsertWindow().state.type_tab()<cr>
        inoremap <buffer> <bs> <Cmd>py3 Xiongkun.InsertWindow().state.type_backspace()<cr>
        inoremap <buffer> <C-w> <Cmd>py3 Xiongkun.InsertWindow().state.delete_word()<cr>
        inoremap <buffer> <space> <Cmd>py3 Xiongkun.InsertWindow().state.type_space()<cr>
        inoremap <buffer> . <Cmd>py3 Xiongkun.InsertWindow().state.type_dot()<cr>
        inoremap <buffer> <C-u> <Cmd>py3 Xiongkun.InsertWindow().state.delete_all()<cr>
        """)
        vim_utils.commands("""
        augroup InsertComplete
            autocmd InsertLeave * py3 Xiongkun.InsertWindow().goto_state(Xiongkun.CloseState(Xiongkun.InsertWindow()))
            autocmd TextChangedI * py3 Xiongkun.InsertWindow().state.insert()
        augroup END
        """)

    def select_string(self):
        select_nr = self.body.buf.cur_cursor_line()
        cur_item = self.body.buf.items[select_nr]
        cur_col = vim_utils.GetCursorXY()[1] - 1 # 1-base -> 0-base
        backspace_num = cur_col - self.start_point + 1
        return "\x08"*backspace_num + cur_item['word']

    def type_enter(self):
        ret = self.select_string()
        self.close_typing_state()
        with vim_utils.VimVariableGuard(ret) as obj:
            return vim.eval(f'feedkeys({obj}, "in")')

    def type_backspace(self):
        cur_col = vim_utils.GetCursorXY()[1] - 1 # 1-base -> 0-base
        if cur_col < self.start_point + 1: 
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

    def type_tab(self):
        self.close_typing_state()
        ret = self.select_string()
        with vim_utils.VimVariableGuard(ret) as obj:
            return vim.eval(f'feedkeys({obj}, "in")')

    def insert(self):
        def fuzzy_filter(word, items):
            from fuzzyfinder import fuzzyfinder
            mapping = { id(item['word']):item for item in items }
            filtered_items = fuzzyfinder(word, [item['word'] for item in items])
            return [ mapping[id(item)] for item in filtered_items ]

        line = vim_utils.GetCurrentLine()
        cur_col = vim_utils.GetCursorXY()[1] - 1
        col = self.start_point
        word = line[col-1:cur_col-1] # | start - end | cursor
        items = fuzzy_filter(word, self.body.buf.items)
        self.body.buf.set_complete_items(items)

    def next(self):
        self.body.buf.on_cursor_move('j')

    def previous(self): 
        self.body.buf.on_cursor_move('k')

    def exit(self):
        print ("exit typing state")
        self.clear_auto()
        self.restore_mapping()

@vim_utils.Singleton
class InsertWindow:
    def __init__(self):
        self.buf = InsertCompleteBuffer()
        self.buf.create()
        self.state = None
        self.goto_state(CloseState(self))

    #@interface
    def complete(self, items, start_point):
        self.set_complete_items(items)
        self.goto_state(TypingState(self, start_point))

    def is_ready(self):
        return isinstance(self.state, CloseState)

    def goto_state(self, state):
        if self.state: 
            self.state.exit()
        self.state = state
        self.state.enter()

    def show(self, col):
        self.move_to_cursor(col)
        self.buf.show()

    def hide(self):
        self.buf.hide()

    def set_complete_items(self, items):
        self.buf.set_complete_items(items)

    def move_to_cursor(self, col):
        col_offset = vim_utils.GetCursorXY()[1] - col
        self.buf.move_to(
           {'line':'cursor+1',
            'col':'cursor-'+str(col_offset), 
            'posinvert': 1,
            'pos': 'topleft'} 
        )
