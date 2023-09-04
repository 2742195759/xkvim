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
            'minwidth': 50,
            'maxheight': 30,
            'minheight': 30,
            'filter': None,
            'pos': 'topleft',
            'line': "cursor+1",
            'col': "cursor",
            'posinvert': 1,
            'padding': [0, 0, 0, 0],
            'border': [0, 0, 0, 0],
            'scrollbar': 1,
        }
        super().__init__(WidgetList("xxx", []), "insert_complete", "", None, self.win_options)
        self.items = []

    def set_complete_items(self, items):
        self.items = items
        self.redraw()

    def make_table(self, items):
        if len(items) == 0: 
            return [""]
        table = [ 
            [ 
                i.get('abbr', i['word']), 
                i['menu'], 
                i['kind'],
            ] 
        for i in items ]
        return vim_utils.print_table(table)

    def onredraw(self):
        self._clear()
        self._put_strings(
            self.make_table(self.items)
        )

@vim_utils.Singleton
class InsertWindow:
    def __init__(self):
        self.buf = InsertCompleteBuffer()
        self.buf.create()

    def show(self):
        self.move_to_cursor()
        self.buf.show()

    def hide(self):
        self.buf.hide()

    def set_complete_items(self, items):
        self.buf.set_complete_items(items)

    def move_to_cursor(self):
        self.buf.move_to(
           {'line':'cursor+1',
            'col':'cursor', 
            'pos': 'topleft'} 
        )

@vim_register(command="TTT")
def TestInsertWindow(args):
    InsertWindow().set_complete_items([{
        'word': 'aaaaa', 
        'abbr': 'a',
        'menu': 'this is addition text',
        'info': 'preview window details.',
        'kind': 'variable', 
    }])
    vim_utils.commands("""
    augroup InsertComplete
        autocmd InsertEnter * py3 Xiongkun.InsertWindow().show()
        autocmd InsertLeave * py3 Xiongkun.InsertWindow().hide()
    augroup END
    """)

