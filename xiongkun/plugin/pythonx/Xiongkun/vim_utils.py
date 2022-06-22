#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File               :   vim_uilts.py
@Time               :   2021-08-21
@Author             :   Kun Xiong
@Contact            :   xk18@mails.tsinghua.edu.cn
@Last Modified by   :   2022-02-10
@Last Modified time :   2022-02-10

This file contain some vim helper function.

called by the other part of the script.
'''

import vim
import os.path as osp
from contextlib import contextmanager
from threading import Lock
from .multiprocess_utils import *
from .log import log

vim_dispatcher = UIDispatcher() # main thread dispatcher, execute a function in main-thread(vim-thread / ui-thread)

class NameGenerator:
    def __init__(self):
        self.current = 0 

    def newname(self):
        self.current += 1 
        return "tmp_%d" % self.current

global_variable = {}
class VimVariable:
    def __init__(self, name="", value=None):
        if name: self._name = name
        else: self._name = global_name_generator.newname()
        if value is not None:
            self.assign(value)

    def assign(self, pyobj):
        global_variable[self._name] = pyobj
        vimcommand('let %s = pyxeval("Xiongkun.global_variable[\'%s\']")' 
            % (self._name, self._name))
        return self

    def delete(self):
        del global_variable[self._name]

    def name(self):
        return self._name

    def __str__(self):
        return self._name

global_name_generator = NameGenerator()

class Location: 
    def __init__(self, name, line, col, base=1):
        self.full_path = osp.abspath(name)
        self.line = line
        self.col = col
        self.base = base

    def getline(self):  
        return self.line 
    
    def getcol(self):   
        return self.col

    def getfile(self):
        return self.full_path

    def to_base(self, new_base):
        col = self.col + new_base - self.base
        row = self.line + new_base - self.base
        return Location(self.full_path, row, col, new_base)

class LocationRange:
    def __init__(self, start_loc, end_loc):
        self.start = start_loc
        self.end = end_loc
        assert (self.start.getfile() == self.end.getfile())

"""
text access and modification function.
"""

def GoToLocation(location, method):
    """
    jump to a location.
    supported method: 
    1. 's': split
    2. 'v': vertical
    3. 't': tabe
    4. '.': current window
    5. 'p': preview open
    """
    if method == '.':
        vimcommand("e +%d %s"%(location.getline(), location.getfile()))
        vimcommand("normal zv")
    elif method == 'p':
        vimcommand("pedit! +%d %s"%(location.getline(), location.getfile()))
        vimcommand("normal zv")

def GetCurrentLine():
    """
    get the line of current cursor.
    """
    return vimeval("getline('.')")

def GetCurrentWord():
    """
    get the line of current cursor.
    """
    return vimeval("expand('<cword>')")


def GetCursorXY():
    """
    get the [int, int] position of cursor.
    """
    return [ int(i) for i in vimeval("getpos('.')")[1:3]]

def SetCurrentLine(text):
    """
    set current line to text.
    """
    lnum, cnum = GetCursorXY()
    return vimeval("setline(%d, '%s')"%(int(lnum), text))

def ReplaceCurrentLine(func):
    new_line = func(GetCurrentLine())
    SetCurrentLine(new_line)

def InsertLinesAtLocation(texts, location):
    if not osp.exists(location.getfile()): 
        lines = []
    else : 
        lines = vimeval("readfile('%s')" % location.getfile())
    final = lines[0:location.getline()-1]
    final.extend(texts)
    final.extend(lines[location.getline()-1:])
    texts = VimVariable().assign(final)
    vimeval("writefile(%s, '%s')" % (texts.name(), location.getfile()))

def SearchToString(word, forward='/'):
    vimcommand("execute 'normal /%s\r' " % word)

def EditFileWithPath(path, method='tabe'):
    vimcommand("%s %s" %(method, path))

def RenderTemplateFile(template_file, **args):
    with open(template_file, "r") as fp:
        lines = fp.readlines()
    from string import Template
    lines = [Template(line).substitute(**args) for line in lines]
    return "".join(lines)

def GetTheLocationOfInclude(filepath):
    with open(filepath, "r") as fp:
        lines = fp.readlines()
    lines = [line.strip() for line in lines]
    find_id = None
    for id, line in enumerate(lines):
        if line.startswith("#include"):
            find_id = id
    if find_id is None: return None
    return Location(filepath, find_id+2, 1)

###########
#
#  Cpp related
#
###########

def InsertIncludeStatementAtLast(filepath, include_text):
    loc = GetTheLocationOfInclude(filepath)
    if loc is not None: InsertLinesAtLocation([include_text], loc)

def IncludePreviewedFile(includes_file=None, included_file=None):
    if includes_file is None: includes_file = CurrentEditFile()
    loc = GetTheLocationOfInclude(includes_file)
    if included_file is None : included_file = GetPreviewWinFile()
    related_path = ToRelatedFilename(included_file)
    InsertIncludeStatementAtLast(includes_file, '#include "%s"' % related_path)
    CurrentBufReload()

def CurrentBufReload():
    vimcommand("checktime")

def SyncCurrentFile():
    vimcommand("e")

def CurrentEditFile(abs=False):
    abs_path = vimeval("expand('%:p')")
    if not abs:
        abs_path = get_git_related_path(abs_path)
    return abs_path

def CurrentWord():
    return vimeval("expand('<cword>')")

def Input(promote=""):
    return vimeval("input('%s')" % promote)

def GetPwd():
    return vimeval("getcwd()")
    
def SetVimRegister(reg, content):
    vimcommand('let @%s="%s"' % (reg, content))

def ToRelatedFilename(filename):
    pwd = GetPwd()
    if filename.startswith(pwd):
        return filename[len(pwd):].strip("/")
    else:   
        print ("Error: can't convert to related path.")

def GetPreviewWinFile():
    tab_info = vimeval('gettabinfo(win_id2tabwin(win_getid(winnr()))[0])')[0]
    wins = tab_info['windows']
    preview_winnr = -1
    for winid in wins:
        win_type = vimeval("win_gettype(win_id2win(%d))" % win)
        if win_type == "preview": 
            preview_winnr = vimeval("(win_id2win(%d))" % win)
    if preview_winnr == -1 : 
        print ("Error: not found preview window")
        return 
    else : 
        return vimeval("bufname(winbufnr(winnr()))")

def YcmJumpFromFunctionCall(call_text, jump_word):
    SetVimRegister("b", call_text)
    vimcommand("put b")
    SearchToString(jump_word, "?")
    vimcommand("sleep 2")
    vimcommand("YcmCompleter GoToDefinition")

def TmpName():
    return vimeval('tempname()')

def ClearCurrent():
    return vimcommand("%d")

def GetLineFromLocation(location):
    """ python read file
    """
    with open(location.getfile(), "r") as fp :
        lines = fp.readlines()
    return lines[location.getline()-1].strip()

def SetQuickFixList(locations, jump=False, cwin=False, textlist=None):
    results = []
    for idx, loc in enumerate(locations): 
        results.append({'filename': loc.getfile(), 
         'lnum': loc.getline(),
         'col': loc.getcol(), 
         'text': GetLineFromLocation(loc) if textlist is None else textlist[idx]})

    qflist = VimVariable().assign(results)
    vimeval('setqflist(%s)' % qflist)
    if jump: 
        vimcommand("cr")
    if cwin: 
        vimcommand("copen")

@contextmanager
def NotChangeQuickfixGuard():
    # TODO (add no change quick fix guard)
    yield

def commands(strs):
    cmds = strs.split("\n")
    for c in cmds:
        vimcommand(c)

def info(*args):
    hi = "Question"
    out = " ".join([a.__str__() for a in args])
    vimcommand("echohl %s" % hi)
    vimcommand("echo '%s'" % out)
    vimcommand("echohl")

def error(*args):
    hi = "Error"
    out = " ".join([a.__str__() for a in args])
    vimcommand("echohl %s" % hi)
    vimcommand("echo '%s'" % out)
    vimcommand("echohl")

def test():
    filename = "/home/data/tmp"
    l = Location(filename, 3, 1)
    InsertLinesAtLocation(['test', 'demo'], l)


    table = [
        ["", "Man Utd", "Man City", "T Hotspur"],
        ["Man Utd", 1, 0, 0],
        ["Man City", 1, 1, 0],
        ["T Hotspur", 0, 1, 2],
    ]

def print_table(table):
    longest_cols = [
        (max([len(str(row[i])) for row in table]) + 3)
        for i in range(len(table[0]))
    ]
    row_format = "".join(["{:>" + str(longest_col) + "}" for longest_col in longest_cols])
    outs = []
    for row in table:
        outs.append(row_format.format(*row))
    return outs

"""
while in py3: see example:  
    UniverseCtrl 
while in vimeval / vimcommand: use 
    vim_format('let a = "%s"', text)
"""
def escape(command, chars="'\\\""):
    l = []
    for c in command:
        if c in chars: l.append("\\" + c)
        else : l.append(c)
    return "".join(l)

def vim_format(template, *args):
    args = [ escape(arg, "\\\"'") for arg in args ]
    return template % tuple(args)

def test():
    print(escape("sdf\\sd\"f", "\\\""))
    text = "['#include \"paddle/fluid/framework/inlined_vector.h\"']"
    print(vimeval(vim_format(""" "%s" """, "\"a\"")))
    print(escape(text, "\\\"'"))
    print(vim_format("TextTrimer(\"%s\")",text))

def vimcommand(cmd):
    vim.command(cmd)
    return
    vim_dispatcher.call(vim.command, [cmd])

def vimeval(cmd):
    ret = vim.eval(cmd)
    return ret
    ret = vim_dispatcher.call(vim.eval, [cmd])
    return ret

def GetTextFromLocation(loc):
    with open(loc.getfile(), "r") as fp :
        lines = fp.readlines()
    if loc.getline() < len(lines): 
        return lines[loc.getline()]
    return None

def GetCursorScreenXY():
    row = int(vim.eval("win_screenpos(winnr())[0]+winline()"))
    col = int(vim.eval("win_screenpos(winnr())[1]+wincol()"))
    return row, col

def Unique(list_like, sig_fn):
    s = set()
    after = []
    for r in list_like:
        sig = sig_fn(r)
        if sig in s: continue
        after.append(r)
        s.add(sig)
    return after

def get_git_related_path(abspath):
    def is_git_director(current):
        return osp.isdir(current) and osp.isdir(osp.join(current, ".git"))
    abspath = osp.abspath(abspath)
    origin = abspath
    def is_root(path):
        return path in ['/', '~']
    while not is_root(abspath) and not is_git_director(abspath): 
        abspath = osp.dirname(abspath)
    if is_root(abspath):
        print ("Can't find git in father directory.")
        return origin
    return origin[len(abspath):].strip("/")

from contextlib import contextmanager 
@contextmanager
def NotChangeRegisterGuard(regs):
    saved = []
    for reg in regs:
        saved.append(vim.eval('getreginfo("%s")'%escape(reg)))
    yield
    v = VimVariable()
    for save, reg in zip(saved, regs):
        v.assign(save)
        vim.eval('setreg("%s", %s)'%(escape(reg), v))
    v.delete()

@contextmanager
def CursorGuard():
    saved = vim.eval('getcurpos()')
    yield
    v = VimVariable()
    v.assign(saved)
    vim.eval(f'setpos(".", {v.name()})')
