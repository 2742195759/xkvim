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

vim.command("set cot=menuone,noselect")

def _StartAutoCompile():# {{{
    cmd = """
augroup ClangdServer
    autocmd!
    autocmd BufReadPost *.cc,*.h,*.cpp call Py_add_document([])
    autocmd TextChanged *.py,*.cc,*.h,*.cpp call Py_did_change([]) 
    autocmd TextChangedI *.py,*.cc,*.h,*.cpp call Py_did_change([]) 
    autocmd CursorMovedI *.py,*.cc,*.h,*.cpp call Py_signature_help([]) 
    autocmd TextChangedI *.py,*.cc,*.h,*.cpp call LSPComplete([])
    autocmd CompleteDonePre *.py,*.cc,*.h,*.cpp call Py_complete_done([v:completed_item])
    autocmd CompleteChanged *.py,*.cc,*.h,*.cpp call Py_complete_select([v:event['completed_item']])
    autocmd InsertLeave * py3 Xiongkun.SignatureWindow().hide()
augroup END
"""
    vim_utils.commands(cmd)# }}}

def _EndAutoCompile():# {{{
    cmd = """
augroup ClangdServer
    autocmd!
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
        _StartAutoCompile()

class LSPServer(RPCServer):
    def __init__(self, remote_server=None):
        self.channel = RPCChannel("LSP", remote_server, "lsp", "Xiongkun.lsp_server()")
        self.call("init", None, FileSystem().getcwd())

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
            markdown_doc = "[LSP Show Message]:" + "\n=================\n" + package['params']['message']
            MessageWindow().set_markdowns([markdown_doc])
            MessageWindow().show()

    def text_document_location(self):
        cur_file = vim_utils.CurrentEditFile(True)
        position = vim_utils.GetCursorXY()
        position = position[0]-1, position[1]-1
        return cur_file, position

class LSPClient:# {{{
    def __init__(self, host):
        self.lsp_server = LSPServer(host)
        self.add_document_for_buffer()

    def add_document_for_buffer(self): 
        buffers = vim_utils.GetBufferList()
        for buffer in buffers:
            buffer = FileSystem().abspath(buffer)
            if not buffer.endswith('/'): self.lsp_server.call("add_document", None, buffer)


    def get_diagnostics(self, filepath):
        self.did_open(filepath)
        json = {
            "method": "get_diags",
            "file": "file://" + do_path_map(osp.abspath(filepath), 'vim', 'clangd'),
        }
        def get_diags(json):
            """
            example of diagnostics: 
            {'jsonrpc': '2.0', 'method': 'textDocument/publishDiagnostics', 'params': {'diagnostics': [{'code': 'access', 'message': "'bar' is a private member of 'MyClass'\n\nhello_world.cpp:5:8: note: implicitly declared private here", 'range': {'end': {'character': 9, 'line': 19}, 'start': {'character': 6, 'line': 19}}, 'severity': 1, 'source': 'clang'}, {'message': "Implicitly declared private here\n\nhello_world.cpp:20:7: error: 'bar' is a private member of 'MyClass'", 'range': {'end': {'character': 10, 'line': 4}, 'start': {'character': 7, 'line': 4}}, 'severity': 3}, {'code': 'undeclared_var_use', 'message': "Use of undeclared identifier 'dasdfs'", 'range': {'end': {'character': 10, 'line': 21}, 'start': {'character': 4, 'line': 21}}, 'severity': 1, 'source': 'clang'}, {'code': '-Wunused-private-field', 'message': "Private field 'foo' is not used", 'range': {'end': {'character': 9, 'line': 3}, 'start': {'character': 6, 'line': 3}}, 'severity': 1, 'source': 'clang', 'tags': [1]}], 'uri': 'file:///home/data/hello_world.cpp', 'version': 0}}
            """
            diags = send_by_python(json, timeout=(10, 10)).json()
            if diags == {}: return
            locs = []
            texts = []
            for diag in diags['params']['diagnostics']: 
                texts.append(diag['message'])
                locs.append(remote_fs.Location(
                    diags['params']['uri'][7:],
                    diag['range']['start']['line']+1, 
                    diag['range']['start']['character']+1))
            vim_utils.vim_dispatcher.call(vim_utils.SetQuickFixList, [locs, True, False, texts])
        threading.Thread(target=get_diags, args=(json,), daemon=True).start()

def goto_definition(args):
    cur_file = vim_utils.CurrentEditFile(True)
    position = vim_utils.GetCursorXY()
    position = position[0]-1, position[1]-1

    def handle(rsp):
        if rsp['result'] is None: 
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

@vim_utils.Singleton
class CompleteResult:
    def set(self, items):
        self.items = items

    def to_locs(self):
        if not hasattr(self, "items"): 
            return []
        kind2type = {
            7: "class", 2: "method", 1: "text", 4: "constructor", 22: "struct", 6: "variable", 3: "function", 14: "keyword",
        }
        results = []
        for item in self.items:
            #if '•' in item['label']: continue  # dont contain other library function.
            r = {}
            r['word'] = item['insertText']
            r['abbr'] = item['label']
            r['info'] = item['document'] if 'document' in item else item['label']
            r['kind'] = kind2type.get(item['kind'], str(item['kind']))
            r['dup'] = 1
            r['user_data'] = item['label']
            results.append(r)
        return results

    def find_item_by_label(self, label):
        for item in self.items:
            if item['label'] == label:
                return item

    def done(self):
        pass

@vim_register(name="LSPComplete")
def complete(args):
    def handle(rsp):
        if 'result' not in rsp or rsp['result'] == None: return
        CompleteResult().set(rsp['result']['items'])
        results = CompleteResult().to_locs()
        def find_start_pos():
            line = vim_utils.GetCurrentLine()
            col = vim_utils.GetCursorXY()[1] - 2 # 1-base -> 0-base
            while col >= 0 and (col >= len(line) or line[col].isalpha() or line[col] in ['_']):
                col -= 1
            return col + 2  # 1 for offset, 2 for 1-base}}}
        # set complete list.
        vim_l = vim_utils.VimVariable().assign(results)
        vim.eval('complete(%d, %s)' % (find_start_pos(), vim_l))
        
    cur_word = vim_utils.CurrentWordBeforeCursor()
    if len(cur_word) < 3 and '.' not in cur_word: return
    cur_file = vim_utils.CurrentEditFile(True)
    position = vim_utils.GetCursorXY()
    position = position[0]-1, position[1]-1
    did_change(args)
    lsp_server().call("complete", handle, cur_file, position)

@vim_register(name="GoToDefinition", command="Def")
def py_goto_definition(args):
    goto_definition(['def'])

@vim_register(name="Py_did_change")
def did_change(args):
    filepath = vim_utils.CurrentEditFile(True)
    content = vim_utils.GetAllLines()
    lsp_server().call("did_change", None, filepath, content, True)

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
            param = sig["parameters"][param_nr]['label']
        function = sig["label"]
        SignatureWindow().set_content(function, param, vim.eval("&ft"))

    did_change([])
    file, pos = lsp_server().text_document_location()
    lsp_server().call("signature_help", handle, file, pos)

@vim_register(name="Py_complete_done")
def complete_done(args):
    if len(args[0]) == 0: return
    label = args[0]['user_data']
    item = CompleteResult().find_item_by_label(label)
    CompleteResult().done()
    GlobalPreviewWindow.hide()

@vim_register(name="Py_add_document")
def add_document(args):
    filepath = vim_utils.CurrentEditFile(True)
    lsp_server().call("add_document", None, filepath)

@vim_register(name="Py_complete_select")
def complete_select(args):
    filepath = vim_utils.CurrentEditFile(True)
    if len(args[0]) == 0: 
        # not selected any.
        return
    label = args[0]['user_data']
    item = CompleteResult().find_item_by_label(label)
    def handle(rsp):
        # set completepopup option to make ui beautiful
        pum_pos = vim.eval("pum_getpos()")
        window_options = {
            "line": int(pum_pos['row']),
            "col" : int(pum_pos['col']) + int(pum_pos['width']) + 2,
            "maxwidth": 70,
            "minwidth": 70,
            "maxheight":15, 
        }
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
        GlobalPreviewWindow.set_showable(
            [PreviewWindow.ContentItem(f" {label}    ", content, vim.eval("&ft"), 1, window_options)])
        GlobalPreviewWindow.show()
        if not content: 
            GlobalPreviewWindow.hide()

    lsp_server().call("complete_resolve", handle, filepath, item)

clangd = None
@vim_register(name="ClangdServerDiags", command="Compile")
def ClangdGetDiags(args):
    if not clangd: return
    clangd.reparse_currentfile(True) # make sure file is the newest.
    time.sleep(0.5)
    clangd.get_diagnostics(vim_utils.CurrentEditFile(True))

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
