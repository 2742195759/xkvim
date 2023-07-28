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

import vim#{{{
import os.path as osp
from contextlib import contextmanager
from threading import Lock
from .multiprocess_utils import *
from .log import log
import socket
from contextlib import closing
import os#}}}

HOME_PREFIX=os.environ["HOME"]

def Singleton(cls):
    instance = None
    def get_instance():
        nonlocal instance
        if instance is None: 
            instance = cls()
        return instance
    return get_instance


def absolute_import(module_name, path):
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location(module_name, path)
    foo = importlib.util.module_from_spec(spec)
    sys.modules["module.name"] = foo
    spec.loader.exec_module(foo)
    return foo


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

def GetCurrentLine():
    """
    get the line of current cursor.
    """
    return vimeval("getline('.')")

def EmptyBuffer(): 
    lines = GetCurrentLine()
    strs = "".join(lines)
    return len(strs) == 0

def GetLine(nr):
    """
    get the line of current cursor.
    """
    return vimeval(f"getline({nr})")

def tempfile():
    return vim.eval("tempname()")

def GetCurrentWord():
    """
    get the line of current cursor.
    """
    return vimeval("expand('<cword>')")

def GetCursorXY(win_id=None):
    """
    get the [int, int] position of cursor. 1-based.
    """
    if win_id is None:
        return [ int(i) for i in vimeval("getpos('.')")[1:3]]
    else: 
        return [ int(i) for i in vimeval(f"getcurpos({win_id})")[1:3]]

def SetCursorXY(x, y):
    vimeval(f"setpos('.', [0, {x}, {y}, 0])")
    vimcommand("normal zv")

def SetLine(lnum, text):
    """
    set line to text.
    """
    text = escape(text, "\"\\")
    log("setline(%d, '%s')"%(int(lnum), text))
    return vimeval('setline(%d, "%s")'%(int(lnum), text))

def SetContent(lines):
    """
    set content to current buffer.
    """
    assert isinstance(lines, str)
    for lnum, text in enumerate(lines.split("\n")):
        SetLine(lnum, text)

def SetCurrentLine(text):
    """
    set current line to text.
    """
    lnum, cnum = GetCursorXY()
    return SetLine(lnum, text)

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

###############
#
#  Cpp related
#
###############

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

def CurrentWordBeforeCursor():
    text = GetCurrentLine()
    _, col = GetCursorXY()
    col -= 2
    start = col + 1
    def pred(ch):
        if ord(ch) >= ord('a') and ord(ch) <= ord('z'):
            return True
        if ord(ch) >= ord('A') and ord(ch) <= ord('Z'):
            return True
        if ch in "_.'\"->/": return True
        return False
    while col >= 0 and (col >= len(text) or pred(text[col])):
        col -= 1
    return text[col+1:start]

def CurrentEditFile(abs=False):
    abs_path = vimeval("expand('%:p')")
    if not abs:
        abs_path = get_git_related_path(abs_path)
    return abs_path

def CurrentWord():
    return vimeval("expand('<cword>')")

def input_no_throw(prompt="", text="", completion=None):
    try:
        if completion: 
            return vimeval(f"input('{prompt}', '{text}', '{completion}')")
        else: 
            return vimeval(f"input('{prompt}', '{text}')")
    except: 
        pass
    return None

def get_char_no_throw():
    try:
        while True:
            c = vim.eval("getchar()")
            # TODO: figure out why lots of '\udc80\udcfd`' is typed.
            if c == '\udc80\udcfd`': continue  
            break
        c = chr(int(c))
    except:
        c = None
    return c


def GetPwd():
    return vimeval("getcwd()")

def GetAllLines(bufnr=None):
    if bufnr == None: bufnr = int(vimeval("bufnr()"))
    if isinstance(bufnr, str): return vimeval(f"getbufline('{bufnr}', 1, '$')")
    if isinstance(bufnr, int): return vimeval(f"getbufline({bufnr}, 1, '$')")

def GetDisplayLines(bufnr=None):
    lines = GetAllLines(bufnr)
    win = VimWindow()
    top, bot = win.display_lines
    return lines[top-1:bot]

def SetDisplayLine(lineno, text, bufnr=None):
    lines = GetAllLines(bufnr)
    win = VimWindow()
    top, bot = win.display_lines
    SetLine(lineno + top, text)

def GetDisplayLine(lineno, text, bufnr=None):
    lines = GetAllLines(bufnr)
    win = VimWindow()
    top, bot = win.display_lines
    return GetLine(lineno + top)
    
def SetVimRegister(reg, content):
    vimcommand('let @%s="%s"' % (reg, escape(content)))

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
        win_type = vimeval("win_gettype(win_id2win(%d))" % winid)
        if win_type == "preview": 
            preview_winnr = vimeval("(win_id2win(%d))" % winid)
    if preview_winnr == -1 : 
        print ("Error: not found preview window")
        return 
    else : 
        return vimeval("bufname(winbufnr(winnr()))")

def IteratorWindowCurrentTab():
    tab_info = vimeval('gettabinfo(win_id2tabwin(win_getid(winnr()))[0])')[0]
    """ [{'windows': [1001, 1372, 1375, 1000], 'variables': {'NERDTreeBufName': 'NERD_tree_1'}, 'tabnr': 1}]
    """
    for win_id in tab_info['windows']: 
        yield win_id

def FindWindowInCurrentTabIf(prediction):
    tab_info = vimeval('gettabinfo(win_id2tabwin(win_getid(winnr()))[0])')[0]
    wins = tab_info['windows']
    finded = -1
    for winid in wins:
        winnr = int(vimeval("(win_id2win(%s))" % winid))
        if prediction(winnr): 
            finded = winnr
    if finded == -1 : 
        return -1
    else : 
        return vimeval(f"winbufnr({finded})")

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

def SetQuickFixList(locations, jump="none", cwin=False, textlist=None):
    # local only function.
    if jump == True: jump = "first"
    assert jump in ['first', 'last', 'none']
    results = []
    for idx, loc in enumerate(locations): 
        results.append({'filename': loc.getfile(), 
         'lnum': loc.getline(),
         'col': loc.getcol(), 
         'text': GetLineFromLocation(loc) if textlist is None else textlist[idx]})

    qflist = VimVariable().assign(results)
    vimeval('setqflist(%s)' % qflist)
    if jump == 'first': 
        vimcommand("cr")
    elif jump == 'last': 
        vimcommand("cr {}".format(len(locations)))
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
    filename = f"{HOME_PREFIX}/tmp"
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
    log("Command: ", cmd)
    vim.command(cmd)

def vimeval(cmd):
    ret = vim.eval(cmd)
    return ret

def GetTextFromLocation(loc):
    loc = loc.to_base(0)
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

def get_git_prefix(abspath):
    origin = abspath
    def is_git_director(current):
        return osp.isdir(current) and osp.isdir(osp.join(current, ".git"))
    abspath = osp.abspath(abspath)
    def is_root(path):
        return path in ['/', '~']
    ans = []
    while not is_root(abspath) :
        if is_git_director(abspath): 
            ans.append(abspath)
        abspath = osp.dirname(abspath)
    if len(ans) == 0: 
        #print ("Can't find git in father directory.")
        #can't find a git path, so we return "" to represent no directory.
        return ""
    return ans[-1]

def get_git_related_path(abspath):
    origin = abspath
    abspath = get_git_prefix(abspath)
    if abspath: 
        return origin[len(abspath):].strip("/")
    return origin

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
    #log("[CursorGuard] Saving :", saved)
    yield
    v = VimVariable()
    v.assign(saved)
    #log("[CursorGuard] Restoring :", saved)
    vim.eval(f'setpos(".", {v.name()})')

@contextmanager
def BufferOptionGuard(option_dict):
    saved_value = {}
    for key, val in option_dict.items():
        saved_value[key] = vim.eval(f"&{key}")
        vim.command(f"let &{key} = '{val}'")
    yield
    for key, val in saved_value.items():
        vim.command(f"let &{key} = '{val}'")

@contextmanager
def CurrentBufferGuard(bufnr=None):
    # NOTE: add options guard to avoid buffer deleted by hidden.
    with BufferOptionGuard({"bufhidden": "hide"}):  
        saved_buf = vim.eval("bufnr()")
        saved_view = vim.eval("winsaveview()")
        if bufnr: vim.command(f'silent keepjumps b {bufnr}')
        yield
        try:
            vim.command(f'silent keepjumps b {saved_buf}')
        except KeyboardInterrupt as e:
            pass
        vim.eval(f"winrestview({dict2str(saved_view)})")

@contextmanager
def CurrentWindowGuard(win_id=None):
    saved_id = vim.eval("win_getid()")
    if win_id is not None: 
        vim.eval(f'win_gotoid({win_id})')
    yield
    vim.eval(f'win_gotoid({saved_id})')

def GoToWindow(wnr):
    win_id = vim.eval(f"win_getid({wnr})")
    vim.eval(f'win_gotoid({win_id})')

@contextmanager
def RedirGuard(name, mode='w'):
    """
    mode in 'w'|'a' for write and append
    if name is a path, redir to a file name.
    if name is a char, redir to a register.
    """
    append = '>'
    if mode == 'a': append = ">>"
    if len(name) == 1: 
        redir_cmd = f"redir @{name}{append}"
    else: 
        redir_cmd = f"redir! {append}{name}"
    vim.command(redir_cmd)
    yield
    vim.command("silent redir END")

def Bufname2Bufnr(name):
    return vim.eval(f"bufnr({name})")

def Notification(msg):
    vim.eval( """ popup_notification("%s", {'line':0, 'col':0}) """ % msg
    )

def memory_buffer():
    vim.command("setlocal nomodifiable")
    vim.command("setlocal buftype=nofile")
    vim.command("setlocal nofoldenable")
    
def GetFileTypeByName(name):
    suffix = os.path.splitext(name)[-1].split('.')[-1]
    dic = {
        "py": "python",
        "cc": "cpp",
        "h": "cpp",
        "cpp": "cpp",
    }
    return dic.get(suffix, "")

def IsBufferExist(file):
    return int(vim.eval(f"bufexists('{file}')")) == 1

def GetBufferList(pattern=None):
    """ get name list by pattern
    """
    last_buf = int(vim.eval("bufnr('$')"))
    ret = []
    for i in range(1, last_buf+1):
        if int(vim.eval(f"buflisted({i})")):  
            ret.append(vim.eval(f"bufname({i})"))
    return ret

def GetVisualWords(replace=True):
    with CursorGuard():
        with NotChangeRegisterGuard('r'):
            vim.command('normal gv"ry')
            text = vim.eval("@r")
            if replace: text.replace("\r", "")
    return text

def WriteIntoTempfile(string):
    fname = tempfile()
    with open(fname, "w") as fp:
        fp.write(string)
    return fname

def WriteVisualIntoTempfile():
    text = GetVisualWords(False)
    return WriteIntoTempfile(text)

def SetVisualWords(strs):
    vim.command('normal gvc{}'.format(
        escape(strs, "'")
    ))

def system(cmd, input=None):
    import subprocess
    child = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
    stdout, stderr = child.communicate(input=input)
    exit_code = child.wait()
    if exit_code != 0: 
        print(f"Error while execute system by arguments: {cmd}")
        print("output: ", stdout)
        print("errors: ", stderr)
        return False, stdout, stderr
    return True, stdout, stderr

def GetCommandOutput(command):
    with NotChangeRegisterGuard('a'): 
        with RedirGuard('a', 'w'): 
            vim.command("silent " + command)
            output = vim.eval("@a")
    return output

@Singleton
class VimKeyToChar:
    def __init__(self):
        self.vim_key_to_char = {
            '\x08': '<bs>',
            '\x04': '<c-d>',
            '\x06': '<c-f>',
            '\x17': '<c-w>',
            '\x15': '<c-u>',
            '\x0b': '<c-k>',
            '\r': '<cr>',
            '\n': '<c-j>',
            ' ' : '<space>',
            '\udc80\udcfd`': "<80><fd>",
            '\udc80kb': "<bs>",
            '\udc80kd': "<down>",
            '\udc80kr': "<right>", 
            '\udc80kl': '<left>',
            '\udc80ku': '<up>',
            '\t': '<tab>',
        }

    def __getitem__(self, key):
        if key in self.vim_key_to_char: 
            return self.vim_key_to_char[key]
        if len(key) > 1: 
            log(f"[VimKeyMap] not supported key found, return ''")
            return ""
        if 1 <= ord(key) <= 26: 
            return f"<c-{chr(ord('a') + ord(key) - 1)}>" 
        return key

@Singleton
class VimKeymap: 
    def __init__(self):
        self.km = {}
        self.init()

    def init(self): 
        def insert(value): 
            self.km[vim.eval('"\{}"'.format(value))] = value.lower()

        for letter in range(65,91):
            letter = chr(letter)
            insert('<c-' + letter + '>')
            insert('<m-' + letter + '>')

        for letter in range(0,10):
            insert('<m-{}>'.format(letter))

        insert ("<up>")
        insert ("<down>")
        insert ("<left>")
        insert ("<right>")
        insert ("<enter>")
        insert ("<cr>")
        insert ("<f1>")

def GetKeyMap():
    return VimKeymap().km

def peek_line(filename, start, end):
    """
    read line from [start, end)
    """
    import linecache
    ret = []
    for i in range(start, end): 
        ret.append(linecache.getline(filename, i).strip())
    return ret

class TextProp:
    def __init__(self, name, bufnr=None, high="Error"):
        if bufnr is None:
            bufnr = int(vimeval("bufnr()"))
        self.bufnr = int(bufnr)
        self.name = name
        prop = {'priority':0, 'highlight': high, 'bufnr': self.bufnr}
        vimeval('prop_type_add("{name}", {dict})'.format(
            name = name, 
            dict = dict2str(prop)
        ))

    def prop_add(self, lnum, col, length=0): 
        config = {
            'type': self.name, 
            'length': length,
            'bufnr': self.bufnr
        }
        vimeval(f'prop_add({lnum}, {col}, {dict2str(config)})')

    def clear(self):
        vimeval("prop_clear(1, 10000000)")

class Matcher:
    def __init__(self):
        self.mid = None
            
    def match(self, high="Error", row_range=None, col_range=None, keyword=None, priority=0): 
        """
            high: highlight group name.
            row_range: (start, end) 
            col_range: (start, end)
            keyword: 
                - None: no key word
                - str : the highlight word
        """
        if keyword is not None:
            keyword = escape(keyword, "~%")
            keyword = escape(keyword, "\\")
        self.delete()
        items = []
        if row_range is not None: 
            start, end = row_range
            items.append(r"\\%>{}l\\&\\%<{}l".format(start, end))
        if col_range is not None: 
            start, end = col_range
            items.append(r"\\%>{}c\\&\\%<{}c".format(start, end))
        if keyword: 
            items.append(keyword)
        cmd = r"\\&".join(items)
        cmd += r"\\c"
        log("Pattern:", cmd)
        self.mid = vim.eval("matchadd(\"{}\", \"{}\", {})".format(
            high, 
            cmd, 
            priority))
        return self

    def match_pos(self, high, row, col, priority=0):
        self.match(high, (row-1, row+1), (col-1, col+1), None, priority)
        return self
        
    def delete(self):
        if self.mid is not None:
            vim.eval(f"matchdelete({self.mid})")
    
class TextPopup:
    def __init__(self, *args, **kwargs):
        self.win_id = None
        self.win_id = self._create(*args, **kwargs)
            
    @classmethod
    def _create(cls, text, screen_row, screen_col, highlight="Normal", z_index=0): 
        win_id = int(vim.eval('popup_create("%s", {"line":%s, "col":%s, "highlight": "%s", "zindex": %d})' % 
            (text, 
             screen_row, 
             screen_col,
             highlight,
             z_index)))
        return win_id
        
    def delete(self):
        if self.win_id is not None:
            vim.eval(f"popup_close({self.win_id})")

def GetWindowCurrentId(): 
    return vimeval("win_getid()")

class VimWindow: 
    def __init__(self, winid=None):
        if winid is None:
            self._id = GetWindowCurrentId()
        else:
            self._id = winid

    @property
    def id(self):
        return int(self._id)

    @property
    def display_rows(self):
        """
        [{'winnr': 3, 'variables': {'airline_lastmode': 'normal', 'paren_hl_on': 0, 'airline_active': 1, 'airline_current_mode': 'COMMAND'}, 'botline': 24, 'height': 24, 'bufnr': 1, 'winbar': 0, 'width': 180, 'tabnr': 1,
 'quickfix': 0, 'topline': 1, 'loclist': 0, 'wincol': 33, 'winrow': 27, 'textoff': 2, 'winid': 1000, 'terminal': 0}]
        """
        out = vimeval(f"getwininfo({self._id})")
        return int(out[0]['topline']), int(out[0]['botline'])

    @property
    def bufnr(self):
        out = vimeval(f"getwininfo({self._id})")
        return int(out[0]['bufnr'])

    def to_screen_pos(self, row, col):
        """
        row and col is 1-based.
        return value is [row,col] also 1-based.
        """
        ret = vimeval(f'screenpos({self.id}, {row}, {col})')
        return int(ret['row']), int(ret['col'])

    @property
    def height(self):
        return int(vim.eval(f"winheight({self.id})"))

    @property
    def width(self):
        return int(vim.eval(f"winwidth({self.id})"))

    def in_window_view(self, row, col):
        """
        is (row, col) in window view ?  all number is 1-based.
        """
        """
        topline is the topmost line, 1-based
        leftcol is the leftmost-1, 0-based
        """
        view = WindowView.find(self.id)
        #topline = int(view['topline'])  
        leftcol = int(view['leftcol'])
        #if row >= topline and row < topline + self.height:   # fold will make this invalid
        if col > leftcol and col < leftcol + self.width + 1:
            return True
        return False

class WindowView:
    cache = {}
    @classmethod
    def clear(cls):
        cls.cache = {}
    @classmethod
    def find(cls, winid):
        # win_saveview = {'lnum': 792, 'leftcol': 0, 'col': 10, 'topfill': 0, 'topline': 778, 'coladd': 0, 'skipcol': 0, 'curswant': 10}
        if winid in cls.cache:
            return cls.cache[winid]
        with CurrentWindowGuard(winid): 
            view = vim.eval("winsaveview()")
            cls.cache[winid] = view
        return view
        
def Normal_GI():
    """ VimInsertQuickPeek
    """
    vim.command("call GI()")

def isLineFolded(num):
    if vim.eval(f"foldclosed({num})") == "-1": return False
    return True

def dict2str(d):
    import json
    return json.dumps(d)

def ui(func):
    def wrapper(*args): 
        log("call ui.")
        vim_dispatcher.call(func, args)
    return wrapper
    
def GetJumpList():
    return vim.eval("getjumplist(winnr())")

def GetConfigByKey(key, directory='./'):
    import yaml  
    # 打开 YAML 文件  
    path = os.path.join(directory, ".vim_config.yaml")
    log(f"[SearchConfig] config_file = {path}")
    if not os.path.exists(path): 
        log(f"[SearchConfig] not exist.")
        return []
    with open(path, 'r') as f:  
        # 读取文件内容  
        data = yaml.safe_load(f)  
    # 输出解析结果  
    if key not in data: return []
    return data[key]

def GetSearchConfig(directory):
    config_lines = GetConfigByKey("search_config", directory)
    from .log import log
    excludes_dir = []
    excludes_file = []
    for line in config_lines: 
        if line.startswith("--exclude-dir="):
            excludes_dir.append(line.split("=")[1].strip()[1:-1])
        elif line.startswith("--exclude="): 
            excludes_file.append(line.split("=")[1].strip()[1:-1])
    log("[SearchConfig]", excludes_dir + excludes_file)
    return excludes_dir, excludes_file

def GetSearchFindArgs(excludes):
    dirs, files = excludes
    find_cmd = []
    for exclude in dirs: 
        find_cmd.append(" ".join(["-not", "-path", f"\"*{exclude}\""]))
    for exclude in files: 
        find_cmd.append(" ".join(["-not", "-name", f"\"*{exclude}\""]))
    log("[FindCmd]: ", find_cmd)
    find_cmd = " -a ".join(find_cmd)
    return find_cmd

def GetSearchGrepArgs(excludes):
    dirs, files = excludes
    grep_cmd = []
    for exclude in dirs: 
        exclude = exclude.replace("/*", "")
        exclude = exclude.replace("/", "")
        grep_cmd.append(f' --exclude-dir="{exclude}" ')
    for exclude in files: 
        grep_cmd.append(f' --exclude="{exclude}" ')
    log("[FindCmd]: ", grep_cmd)
    return grep_cmd

def GetSearchFilesFromCommand(find_cmd):
    log("[FindCmd]: ", find_cmd)
    files = []
    for line in vim.eval("system('{cmd}')".format(cmd=find_cmd)).split("\n"):
        line = line.strip()
        if line and os.path.isfile(line):
            files.append(line)
    return files

def GetSearchFiles(directory):
    base_cmd = f"find {directory} "
    excludes = GetSearchConfig(directory)
    find_args = GetSearchFindArgs(excludes)
    find_cmd = base_cmd + find_args
    return GetSearchFilesFromCommand(find_cmd)

class PopupList:
    # depends on vim_quick#ui
    def __init__(self, items):
        self._items = items
        
    def show(self): 
        _item_var = VimVariable().assign(self._items)
        log("[PopupList]: ", 'call quickui#context#open(%s, {})' % _item_var)
        vim.command('call quickui#context#open(%s, {})' % _item_var)

def StringWidth(string):
    return int(vim.eval(f"strwidth('{string}')"))

def StringBytes(string):
    return int(vim.eval(f"len('{string}')"))

def TotalWidthHeight():
    return int(vim.eval("&columns")), int(vim.eval("&lines"))

def getHomeDirectory(): 
    return HOME_PREFIX

def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]
