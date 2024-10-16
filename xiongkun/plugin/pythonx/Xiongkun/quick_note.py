import vim
import sys
import os
import os.path as osp
from .func_register import *
from .vim_utils import *
from collections import OrderedDict
from .buf_app import Buffer, CreateWindowLayout, Application

time_note = "/home/data/time_note.txt"

def find_next(strs, start, str=""):
    """ [  )
    """
    while len(strs) > start and not strs[start].startswith(str): 
        start = start + 1
    return start

class TimeNotes:
    def __init__(self, time="", title="", detail=""):
        self.time = time
        self.title = title
        self.detail = detail

    def toString(self):
        s = ""
        s +=  f"===== Title  =====\n"
        s += f"{self.title}\n"
        s +=  f"===== Time   =====\n"
        s += f"{self.time}\n"
        s +=  f"===== Detail =====\n"
        s += f"{self.detail}"
        return s

    def fromString(self, strings):
        strs = strings.split("\n")
        i = -1
        while (i+1) < len(strs):
            i += 1
            line = strs[i].strip()
            if line.startswith("===== Title"): 
                self.title = "\n".join(strs[i+1:find_next(strs, i+1, "=====")])
                continue
            if line.startswith("===== Time"): 
                self.time = "\n".join(strs[i+1:find_next(strs, i+1, "=====")])
                continue
            if line.startswith("===== Detail"): 
                self.detail = "\n".join(strs[i+1:find_next(strs, i+1, "=====")])
                continue
    
class TimeNoteEditBuffer(Buffer):
    def __init__(self, note=None):
        super().__init__("TimeNoteEdit", None, None)
        self.syntax = "timenote"
        self.note = note 
        if note == None: self.note = TimeNotes()

    def oninit(self):
        if self.syntax: 
            vim.command(f'set syntax={self.syntax}')
        vim.command(f'set buftype=acwrite')
        vim.command(f'setlocal modifiable')

    def onredraw(self):
        self._clear()
        texts = self.note.toString().split('\n')
        self._put_strings(texts)
        vim.command(f"normal! gg")

    def on_save_and_quit(self):
        # you can quit in the buffer.
        vim.command(f"set nomodified")
        all_lines = "\n".join(GetAllLines())
        self.note.fromString(all_lines)
        with open(time_note, "a") as fp:  
            fp.write(self.note.toString() + "\n\n\n")

    def on_tab(self, x, y):
        all_lines = GetAllLines()
        next_line = find_next(all_lines, GetCursorXY()[0]-1, "=====") + 2
        if next_line <= len(all_lines): SetCursorXY(next_line, 1)
        else: SetCursorXY(2, 1)

    def auto_cmd(self, cmd):
        if cmd == None: 
            return [ "BufWriteCmd", ]
        if cmd == "BufWriteCmd": self.on_save_and_quit()

    def get_keymap(self):
        """ some special key map for example.
        """
        return {
            '<c-j>': self.on_tab,
            'i:<c-j>': self.on_tab,
        }

class TimeNoteEditApp(Application):
    def __init__(self):
        super().__init__()
        self.layout = CreateWindowLayout(cmds=["tabe"], active_win="win")
        self.mainbuf = TimeNoteEditBuffer()

    def start(self):
        self.layout.create()
        self.mainbuf.create()
        self.layout.set_buffer("win", self.mainbuf)
        vim.command(f'set nomodified')

class SnippetEditBuffer(Buffer):
    def __init__(self, name):
        self.current_filetype = vim.eval("&ft")
        super().__init__("SnippetEditBuffer", None, None)
        self.texts = GetVisualWords().split("\n")
        self.snip_name = name

    def oninit(self):
        vim.command(f'set buftype=acwrite')
        vim.command(f'setlocal modifiable')
        vim.command(f"set ft={self.current_filetype}")

    def onredraw(self):
        self._clear()
        self._put_strings(self.texts)
        vim.command(f"normal! gg")

    def on_save_and_quit(self):
        # you can quit in the buffer.
        vim.command(f"set nomodified")
        all_lines = "\n".join(GetAllLines())
        vim.command("UltiSnipsEdit")
        filename = vim.eval("bufname()")
        with open(filename, "a") as fp:  
            fp.write(f"\nsnippet {self.snip_name} ")
            fp.write('"no description"\n')
            fp.write(all_lines)
            fp.write("\nendsnippet")
        vim.command("bwipeout")
        vim.command("call UltiSnips#RefreshSnippets()")

    def auto_cmd(self, cmd):
        if cmd == None: 
            return [ "BufWriteCmd", ]
        if cmd == "BufWriteCmd": 
            bufnr = vim.eval("bufnr()")
            self.on_save_and_quit()
            vim.command(f"b #")
            vim.command(f"bwipeout {bufnr}")

class SnippetEditApp(Application):
    def __init__(self, name):
        super().__init__()
        self.layout = CreateWindowLayout(cmds=["tabe"], active_win="win")
        self.mainbuf = SnippetEditBuffer(name)

    def start(self):
        self.layout.create()
        self.mainbuf.create()
        self.layout.set_buffer("win", self.mainbuf)
        vim.command(f'set nomodified')

@vim_register(command="TN", with_args=True)
def TestNoteEdit(args):
    print (args)
    if args[0] == 'h' or len(args) > 1: 
        print("TimeNote Help:")
        print("    TN ls : list the all timenotes.")
        print("    TN e  : edit a new timenote.")
    if args[0] == 'ls': 
        with open(time_note, "r") as fp :
            lines = fp.readlines()
        print ("".join(lines))
    if args[0] == 'e':
        ff = TimeNoteEditApp()
        ff.start()

@vim_register(command="AddSnippet", with_args=False)
def AddSnippet(args):
    name = input_no_throw("输入Snippet名称: ")
    if name is None: return
    ff = SnippetEditApp(name)
    ff.start()
