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
from .command_doc_popup import DocPreviewBuffer
from .clangd_client_utils import get_content_deltas

vim.command("set cot=menuone,noselect")
vim.command("set scl=yes")

is_disabled = False

auto_files = [
    '*.py',
    '*.cc',
    '*.h',
    '*.cpp',
    '*.cpp',
    '*.hs',
    '*.haskell',
    '*.md',
]

def _StartAutoCompile():# {{{
    files = ",".join(auto_files)
    cmd = """
augroup ClangdServer
    autocmd!
    autocmd TextChanged {auto_files} call Py_did_change([1]) 
    autocmd TextChangedI {auto_files} call Py_complete([])
    autocmd CursorMovedI {auto_files} call Py_signature_help([]) 
    autocmd CompleteDonePre {auto_files} call Py_complete_done([v:completed_item])
    autocmd CompleteChanged {auto_files} call Py_complete_select([v:event['completed_item']])
    autocmd InsertLeave * py3 Xiongkun.SignatureWindow().hide()
augroup END
"""
    cmd = cmd.format(auto_files=files)
    vim_utils.commands(cmd)# }}}

def _EndAutoCompile():# {{{
    cmd = """
augroup ClangdServer
    autocmd!
    autocmd TextChanged {auto_files} call Py_did_change([1]) 
augroup END
"""
    vim_utils.commands(cmd)# }}}

@contextmanager
def StopAutoCompileGuard():# {{{
    """ with this guard, all autocmd `ClangdServer` will not compile. 
    """
    try:
        _EndAutoCompile()
        yield
    finally:
        if not is_disabled:
            _StartAutoCompile()
    
@vim_utils.Singleton
class LSPDiagManager: 
    def __init__(self):
        # define sign
        self.id = 1000
        vim.command("sign define lsp_warn  text=>> texthl=Search")
        vim.command("sign define lsp_error text=>> texthl=Error")
        vim.eval("prop_type_add('lsp_message', {'highlight': 'Error'})")

    def next_id(self):
        ret = self.id
        self.id += 1
        return ret

    def _place(self, sign_name, file, line, message):
        id = self.next_id()
        if not FileSystem().bufexist(file): return
        vim.command(f"sign place {id} line={line} name={sign_name} file={file}")
        config = {
            'bufnr': file,
            'id': id,
            'text': message,
            'text_align': 'right',
            'type': 'lsp_message',
            'text_wrap': 'wrap'
        }
        try:
            vim.eval(f"prop_add({line}, 0, {json.dumps(config)})")
        except: 
            # change while diagnostic sending will cause invalid {line} exception.
            pass

    def error(self, file, line, message=""): 
        self._place("lsp_error", file, line, message)

    def warn(self, file, line, message=""):
        return
        self._place("lsp_warn", file, line, message)
    
    def clear(self, file):
        if not FileSystem().bufexist(file): return
        vim.command(f"sign unplace * file={file}")
        config = { 'bufnr': file, 'type': 'lsp_message', 'all': 1 }
        vim.eval(f"prop_remove({json.dumps(config)})")

class FileSyncManager:
    """
    0. Sync the file between LSP.
    1. Compare the diff between last buffer content and current buffer content. 
    2. Send the diff into lsp.
    """
    def __init__(self, lsp):
        self.lastContent = {} # bufname -> Content
        self.lsp = lsp

    def did_change(self, filepath, want_diagnostic=True):
        abspath = FileSystem().abspath(filepath)
        assert FileSystem().bufexist(abspath)
        new_content = vim_utils.GetAllLines(abspath)
        if abspath not in self.lastContent: 
            self.lastContent[abspath] = new_content
            self.lsp.notification("did_change", filepath, new_content, True)
            return 
            
        old_content = self.lastContent[abspath]
        diff = self.cal_diff(new_content, old_content)
        self.lastContent[abspath] = new_content
        if diff:
            self.lsp.notification("did_change", filepath, diff, want_diagnostic)

    def cal_diff(self, new_content, old_content):
        return get_content_deltas(old_content, new_content)

class VersionChecker:
    def __init__(self):
        self.id2bufhash = {} # request_id -> buf_hash
    def save_version(self, id):
        content = "\n".join(vim_utils.GetAllLines())
        self.id2bufhash[id] = hash(content)
    def check_version(self, id):
        assert id in self.id2bufhash
        content = "\n".join(vim_utils.GetAllLines())
        return self.id2bufhash[id] == hash(content)

class CancelManager:
    def __init__(self, server):
        self.server = server
        self.file2ids = {}
    def add_request(self, idx, filepath): 
        abspath = FileSystem().abspath(filepath)
        if abspath not in self.file2ids: 
            self.file2ids[abspath] = set()
        self.file2ids[abspath].add(idx)
    def remove_request(self, idx, filepath):
        abspath = FileSystem().abspath(filepath)
        if abspath in self.file2ids: 
            self.file2ids[abspath].remove(idx)
    def cancel(self, filepath):
        abspath = FileSystem().abspath(filepath)
        if abspath in self.file2ids: 
            for idx in self.file2ids[abspath]:
                print (f"cancel {idx}")
                self.server.call("cancel", None, filepath, idx)
                if id in self.server.channel.callbacks: del self.server.channel.callbacks[idx]

def show_diagnostics_in_textprop(package):
    """ 
    show diagnostics in textprop
    1. nice for print
    2. some bugs
    3. not easy for debug, for a good debug show method, see `show_diagnostics_in_quickfix`
    """
    file = package['params']['uri'][7:]
    file = FileSystem().abspath(file)
    LSPDiagManager().clear(file)
    diags = package['params']['diagnostics']
    for diag in diags:
        line = diag['range']['start']['line'] + 1
        if diag['severity'] == 1:
            LSPDiagManager().error(file, line, diag['message'])
        elif diag['severity'] == 2:
            LSPDiagManager().warn(file, line, diag['message'])

def show_diagnostics_in_quickfix(package):
    file = package['params']['uri'][7:]
    file = FileSystem().abspath(file)
    bufnr = int(vim.eval(f"bufnr('{file}')"))
    LSPDiagManager().clear(file)
    diags = package['params']['diagnostics']
    qflist = []
    for diag in diags:
        line = diag['range']['start']['line'] + 1
        qflist.append({
            'bufnr': bufnr,
            'filename': file,
            'lnum': line,
            'text': diag['message'],
            'type': ["/", "E", "W"][diag['severity']],
        })
    vim_utils.SetQuickFixListRaw(qflist, "first", cwin=True)

class LSPServer(RPCServer):
    def __init__(self, remote_server=None):
        self.channel = RPCChannel("LSP", remote_server, "lsp", "Xiongkun.lsp_server()", noblock=1)
        self.version_checker = VersionChecker()
        self.file_manager = FileSyncManager(self)
        self.id = 0
        self.notification("init", FileSystem().getcwd())
        self.hooker = {}
        self.hooker_identifier = 0
        self.register_default_publishdiagnostics()

    def register_default_publishdiagnostics(self):
        def default_hander(package):
            if is_disabled: 
                return None
            show_diagnostics_in_textprop(package)
        self.register_hooker("textDocument/publishDiagnostics", default_hander)
        
    def register_hooker(self, method, func): 
        # return index, we can use index to remove hooker.
        hookers = self.hooker.get(method, {})
        current_id = self.hooker_identifier
        self.hooker_identifier += 1
        hookers[current_id] = func
        self.hooker[method] = hookers
        return current_id

    def register_once(self, method, func): 
        # return index, we can use index to remove hooker.
        identi = self.register_hooker(method, func)
        origin = self.hooker[method][identi]
        def func(x):
            origin(x)
            self.remove_hooker(method, identi)
        self.hooker[method][identi] = func
        return None

    def remove_hooker(self, method, identi):
        hooker = self.hooker.get(method, {})
        assert identi in hooker
        del hooker[identi]

    def fire_hooker(self, package):
        assert 'method' in package
        funcs = list(self.hooker.get(package['method'], {}).values())
        for hook in funcs:
            hook(package)
        return None

    def receive(self): # for hooker.
        msg = vim.eval(f"{self.channel.receive_name}")
        if not msg: return
        id, is_finished, output = json.loads(msg)
        if id == -1 and "method" in output: 
            return self.handle_method(output)
        return self.channel.on_receive(msg)

    def handle_method(self, package):
        from .windows import MessageWindow
        if package["method"] == "window/showMessage":
            # show message by window.
            markdown_doc = "[LSP Show Message]:" + "\n=================\n" + package['params']['message']
            MessageWindow().set_markdowns([markdown_doc])
            MessageWindow().show()
        elif 'method' in package:
            self.fire_hooker(package)

    def notification(self, name, *args):
        stream = self.channel.stream_new(-1)
        stream.send(name, None, *args)

    def call(self, name, on_return, *args):
        def lsp_handle_wrapper(rsp):
            if self.version_checker.check_version(rsp['id']):
                return on_return(rsp)
        return_handle = on_return
        if self.is_version_api(name):
            return_handle = lsp_handle_wrapper
        stream = super().call(name, return_handle, *args)
        if self.is_version_api(name):
            self.version_checker.save_version(stream.id)

    def is_version_api(self, name):
        return name in ['complete', 'complete_resolve', 'signature_help']

    def text_document_location(self):
        cur_file = vim_utils.CurrentEditFile(True)
        position = vim_utils.GetCursorXY()
        position = position[0]-1, position[1]-1
        return cur_file, position

class LSPClient:# {{{
    def __init__(self, host):
        self.host = host
        self.lsp_server = LSPServer(host)

def goto_definition(args):
    did_change([False])
    cur_file = vim_utils.CurrentEditFile(True)
    position = vim_utils.GetCursorXY()
    position = position[0]-1, position[1]-1

    def handle(rsp):
        if 'result' not in rsp or rsp['result'] is None: 
            print ("Definition No Found !")
            return []
        all_locs = lsp_to_location( rsp['result'] )
        if len(all_locs) == 0: 
            print ("Definition No Found !")
            return []
        if len(all_locs) == 1:
            first_loc = all_locs[0]
            log("[Clangd Get Result]", first_loc.getfile())
            remote_fs.GoToLocation(first_loc, '.')
        else: 
            GlobalPreviewWindow.set_locs(all_locs)
            GlobalPreviewWindow.show()
    if args[0] == 'def': 
        lsp_server().call("goto", handle, cur_file, "definition", position)
    elif args[0] == 'ref': 
        lsp_server().call("goto", handle, cur_file, "implementation", position)


def ultisnip_complete_items():
    snippets = vim.eval("UltiSnips#SnippetsInCurrentScope()")
    results = []
    for name, descri in snippets.items():
        r = {}
        r['word'] = name
        r['abbr'] = name
        r['info'] = descri
        r['kind'] = "UltiS"
        r['dup'] = 1
        r['user_data'] = {'type': 'ulti', 'origin': descri}
        results.append(r)
    return results

def lsp_complete_items(rsp):
    if 'result' not in rsp or rsp['result'] == None: return []
    items = rsp['result']['items']
    kind2type = {
        7: "class", 2: "method", 1: "text", 4: "constructor", 22: "struct", 6: "variable", 3: "function", 14: "keyword", 9: "module",
    }
    results = []
    for item in items:
        r = {}
        r['word'] = item.get('insertText', item.get('label'))
        r['abbr'] = item['label']
        r['info'] = item['document'] if 'document' in item else item['label']
        r['kind'] = kind2type.get(item['kind'], str(item['kind']))
        r['dup'] = 1
        r['user_data'] = {'type': 'lsp', 'origin': json.dumps(item)}
        results.append(r)
    return results

vim.command("""
inoremap <m-n> <cmd>call Py_complete ([])<cr>
"""
)
@vim_register(name="Py_complete")
def complete(args):
    def handle(rsp):
        totals = ultisnip_items
        if not vim.eval("mode()").startswith('i'): return
        totals = lsp_complete_items(rsp) + totals
        def find_start_pos():
            line = vim_utils.GetCurrentLine()
            col = vim_utils.GetCursorXY()[1] - 2 # 1-base -> 0-base
            while col >= 0 and (col >= len(line) or line[col].isalpha() or line[col] in ['_']):
                col -= 1
            return col + 2  # 1 for offset, 2 for 1-base}}}
        # set complete list.
        obj = vim_utils.VimVariable().assign(totals)
        vim.eval('complete(%d, %s)' % (find_start_pos(), obj))
        
    ultisnip_items = ultisnip_complete_items()
    cur_word = vim_utils.CurrentWordBeforeCursor()
    if len(cur_word) < 1 and '.' not in cur_word: return
    cur_file = vim_utils.CurrentEditFile(True)
    position = vim_utils.GetCursorXY()
    position = position[0]-1, position[1]-1
    did_change([True])
    lsp_server().call("complete", handle, cur_file, position)

@vim_register(name="GoToDefinition", command="Def")
def py_goto_definition(args):
    goto_definition(['def'])

@vim_register(name="Py_did_change")
def did_change(args):
    filepath = FileSystem().abspath(vim_utils.CurrentEditFile(True))
    if args[0] == "1": args[0] = True
    lsp_server().file_manager.did_change(filepath, args[0])

@vim_utils.Singleton
class SignatureWindow(DocPreviewBuffer):
    def __init__(self):
        options = {
            "maxheight": 1,
            "line": "cursor-1",
            "col" : "cursor",
            "title": "",
            "border": [0, 0, 0, 0],
        }
        self.content = ""
        self.param = ""
        self.syntax = ""
        super().__init__(options)
        
    def set_content(self, function, param, syntax):
        self.content = function
        self.param = param
        self.syntax = syntax
        self.redraw()
        self.show()

    def hide(self):
        self.execute(f"match none")
        super().hide()

    def onredraw(self):
        self._clear()
        if self.content: self._put_strings(self.content)
        if self.syntax: self.execute(f'set syntax={self.syntax}')
        if self.param : self.execute(f"match Search /{self.param}/")

@vim_register(name="Py_signature_help")
def signature_help(args):
    def handle(rsp):
        if not vim.eval("mode()").startswith('i'): return 
        debug(rsp)
        if 'result' not in rsp or rsp['result'] == None:
            SignatureWindow().hide()
            return
        result = rsp['result']
        sigs = result['signatures']
        if not len(sigs): return 
        sig = result['signatures'][result['activeSignature']]
        param = ""
        if 'activeParameter' in result: 
            param_nr = result['activeParameter'] 
            if 'activeParameter' in sig: 
                param_nr = sig['activeParameter']
            if param_nr < len(sig["parameters"]): 
                param = sig["parameters"][param_nr]['label']
        function = sig["label"]
        SignatureWindow().set_content(function, param, vim.eval("&ft"))

    file, pos = lsp_server().text_document_location()
    did_change([True])
    lsp_server().call("signature_help", handle, file, pos)

@vim_register(name="Py_complete_done")
def complete_done(args):
    # do nothing.
    if len(args[0]) == 0: return
    GlobalPreviewWindow.hide()

@vim_register(name="Py_complete_select")
def complete_select(args):
    def show_info(title, content):
        pum_pos = vim.eval("pum_getpos()")
        if len(pum_pos) == 0: return
        window_options = {
            "line": int(pum_pos['row']),
            "col" : int(pum_pos['col']) + int(pum_pos['width']) + 2,
            "maxwidth": 70,
            "minwidth": 70,
            "maxheight":15, 
        }
        GlobalPreviewWindow.tmp_window()
        GlobalPreviewWindow.set_showable(
            [PreviewWindow.ContentItem(title, content, vim.eval("&ft"), 1, window_options)])
        GlobalPreviewWindow.show()
        if not content: 
            GlobalPreviewWindow.hide()

    if len(args[0]) == 0: return
    filepath = vim_utils.CurrentEditFile(True)
    user_data = args[0]['user_data']
    if user_data['type'] == "lsp": 
        def handle_lsp(rsp):
            # set completepopup option to make ui beautiful
            def get_content(rsp):
                if "result" not in rsp or rsp['result'] is None:
                    rsp = {'result': item}
                content = []
                rsp = rsp['result']
                if 'detail' in rsp: 
                    content.extend(rsp['detail'].split("\n"))
                    content.append("")
                if 'documentation' in rsp: 
                    content.append("===========Documentation=========")
                    content.extend(rsp['documentation']['value'].split("\n"))
                return content
            content = get_content(rsp)
            show_info(f"   LSP   ", content)
        item = json.loads(user_data['origin'])
        lsp_server().call("complete_resolve", handle_lsp, filepath, item) 

    if user_data['type'] == 'ulti': 
        def handle_ulti(rsp):
            show_info("   Ulti   ", rsp['result'])
        lsp_server().call("echo", handle_ulti, user_data['origin'])


clangd = None
@vim_register(command="LSPDisableFile", with_args=True)
def PyDisableFile(args):
    suffix = args[0]
    lsp_server().call("disable_file", None, suffix)

@vim_register(command="LSPDisable")
def LSPDisable(args):
    _EndAutoCompile()

@vim_register(command="LSPDiags")
def LSPGetDiags(args):
    def handler(package):
        show_diagnostics_in_quickfix(package)
    did_change([True])
    lsp_server().register_once("textDocument/publishDiagnostics", handler)

@vim_register(command="LSPRestart")
def LSPRestart(args):
    global clangd
    if clangd is None: 
        print ("lsp is not start yet. run SetRPCProject to open it.")
        return 
    _EndAutoCompile()
    _StartAutoCompile()
    clangd = LSPClient(clangd.host)

def lsp_to_location(result):# {{{
    loc = []
    for r in result:
        loc.append(remote_fs.Location(r['uri'][7:], r['range']['start']['line']+1, r['range']['start']['character']+1))
    return loc# }}}

def lsp_server():
    global clangd
    if clangd is None: 
        _EndAutoCompile()
        _StartAutoCompile()
        clangd = LSPClient(f"127.0.0.1:{RPCChannel.local_port}")
    return clangd.lsp_server

@vim_register(command="LSPDisable")
def lsp_disable(args):
    global is_disabled
    is_disabled=True
    _EndAutoCompile()

def set_remote_lsp(config_file):
    _EndAutoCompile()
    _StartAutoCompile()
    global clangd
    import yaml  
    if not os.path.exists(config_file): 
        print ("not exist.")
        return
    with open(config_file, 'r') as f:  
        data = yaml.safe_load(f)  
    host = data['host']
    clangd = LSPClient(host)
