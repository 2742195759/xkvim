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
from .windows import GlobalPreviewWindow
import time

def do_path_map(path, fr="clangd", to="vim"):
    """
    prefix = None to disable the path map.
    """
    prefix = {"vim": "/home/ssd2", "clangd": "/home/data/xiongkun"}
    prefix = None
    if prefix is None:
        return path
    if not path.startswith(prefix[fr]): 
        raise RuntimeError(f"Got `{fr}` path: `{path}`, which is not found in vim client.")
    return prefix[to] + path[len(prefix[fr]):]

client_id = str(random.randint(1, 10000))
clangd = None

def _StartAutoCompile():# {{{
    cmd = """
augroup ClangdServer
    autocmd!
    autocmd BufEnter *.cc,*.h,*.cpp cal ClangdDidOpen([expand('%:p')])
    autocmd VimEnter * cal ClangdServerStart([])
    autocmd VimLeave * cal ClangdServerExit([])
    autocmd BufWritePost *.cc,*.h,*.cpp cal ClangdServerReparse([expand('%:p')])
augroup END
"""
    if int(vim.eval("g:enable_clangd")): 
        vim_utils.commands(cmd)# }}}

def _EndAutoCompile():# {{{
    cmd = """
augroup ClangdServer
    autocmd!
augroup END
"""
    if int(vim.eval("g:enable_clangd")): 
        vim_utils.commands(cmd)# }}}

@contextmanager
def StopAutoCompileGuard():# {{{
    """ with this guard, all autocmd `ClangdServer` will not compile. 
    """
    try:
        _EndAutoCompile()
        yield
    finally:
        _StartAutoCompile()# }}}

def send_by_python(json_req=None, cmd=None, url="http://10.255.125.22:10003", timeout=(2,2), **args):# {{{
    """ 
    """
    import json
    import requests
    if 'http_proxy' in os.environ: del os.environ['http_proxy']
    if 'https_proxy' in os.environ: del os.environ['https_proxy']
    headers = {"Content-Type":"application/json", "port": "2000", 'client_id':client_id}
    if cmd != None: 
        headers['cmd'] = cmd
        headers.update(**args)
        return requests.post(url, data=json.dumps({}), headers=headers)
    assert json_req is not None, "json_req can't be empty."
    try:
        rsp = requests.post(url, data=json.dumps(json_req), headers=headers, timeout=timeout)
        return rsp
    except:
        return None
        # }}}

def clangd_initialize(id):# {{{
    json = {
        "jsonrpc": "2.0",
        "id" : str(id),
        "method": "initialize",
        "params": {}
    }
    send_by_python(json)# }}}

def clangd_add_document(filepath="/home/data/hello_world.cpp"):# {{{
    with open(filepath, 'r') as fp:
        content = fp.readlines()
    content = "".join(content)
    #print (content)
    json = {
        "jsonrpc": "2.0",
        "method": "textDocument/didOpen",
        "params": {
            "textDocument": {
                "uri": "file://" + do_path_map(filepath, "vim", "clangd"),
                "languageId": "cpp",
                "text": content,
            },
        }
    }
    # we just want to run util end.
    threading.Thread(target=send_by_python, args=(json,), daemon=True).start()
# }}}

def clangd_goto(id, filepath="/home/data/hello_world.cpp", method="definition", pos=(0,0)):# {{{
    json = {
        "jsonrpc": "2.0",
        "id": str(id),
        "method": "textDocument/%s" % method,
        #"method": "textDocument/implementation",
        "params": {
            "textDocument": {
                "uri": "file://" + do_path_map(filepath, "vim", "clangd"),
            },
            "position": {
                "line": pos[0], 
                "character" : pos[1] 
            }
        }
    }
    return send_by_python(json)# }}}

def clangd_complete(id, filepath, pos=(0,0)):# {{{
    json = {
        "jsonrpc": "2.0",
        "id": str(id),
        "method": "textDocument/completion",
        "params": {
            "limit": 20,
            "context": {
                "triggerKind": 1, # invoke trigger.
            },
            "textDocument": {
                "uri": "file://" + do_path_map(filepath, "vim", "clangd"),
            },
            "position": {
                "line": pos[0], 
                "character" : pos[1],
            },
        }
    }
    return send_by_python(json, timeout=(5, 5))# }}}

class Clangd():# {{{
    def _getid(self):
        self.id += 1
        return self.id

    def _lastid(self):
        return self.id

    def __init__(self):
        self.id = 1
        clangd_initialize(self._getid())
        self.loaded_file = set()

    # non block
    def did_open(self, filepath):
        if filepath not in self.loaded_file:
            clangd_add_document(filepath)
            self.loaded_file.add(filepath)

    # non block
    def getContentChanges(self, filepath, content):
        return {
            'range': None, 
            'rangeLength': None,
            'text': content
        }

    def reparse_currentfile(self, want_diag=False):
        content = None
        lines = vim.eval("getbufline(bufnr(), 1, '$')")
        if want_diag == True: lines += [" "]
        self.reparse(vim_utils.CurrentEditFile(True), "\n".join(lines), want_diag)

    def _construct_reparse_request(self, filepath, content, want_diag=True):
        param = {
            "textDocument": {
                "uri": "file://" + do_path_map(filepath, "vim", "clangd"),
            },
            "contentChanges": [self.getContentChanges(filepath, content)],
            "wantDiagnostics": want_diag,
            "forceRebuild": False,
        }
        json = {
            "jsonrpc": "2.0",
            "method": "textDocument/didChange",
            "params": param,
        }
        return json

    def reparse(self, filepath, content, want_diag):
        self.did_open(filepath)
        json = self._construct_reparse_request(filepath, content, want_diag)
        threading.Thread(target=send_by_python, args=(json,), daemon=True).start()

    def get_diagnostics(self, filepath):
        self.did_open(filepath)
        json = {
            "method": "get_diags",
            "file": "file://" + do_path_map(osp.abspath(filepath), 'vim', 'clang'),
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
                locs.append(vim_utils.Location(
                    uri2abspath(diags['params']['uri']),
                    diag['range']['start']['line']+1, 
                    diag['range']['start']['character']+1))
            vim_utils.vim_dispatcher.call(vim_utils.SetQuickFixList, [locs, True, False, texts])
        threading.Thread(target=get_diags, args=(json,), daemon=True).start()
    # block
    def goto_def(self, filepath, position):
        id = self._getid()
        self.did_open(filepath)
        rsp = clangd_goto(id, filepath, 'definition', position)
        if rsp is None:
            return None
        rsp = [json.loads(rsp.content)]
        return [r for r in rsp if r.get('id', -1) == str(id)][0]

    def goto_ref(self, filepath, position):
        id = self._getid()
        self.did_open(filepath)
        rsp = clangd_goto(id, filepath, 'references', position)
        if rsp is None:
            return None
        rsp = [json.loads(rsp.content)]
        return [r for r in rsp if r.get('id', -1) == str(id)][0]

    def complete(self, filepath, position):
        id = self._getid()
        self.did_open(filepath)
        rsp = clangd_complete(id, filepath, position)
        if rsp is None: return None
        rsp = json.loads(rsp.content)
        kind2type = {# {{{
            7: "c", 2: "m", 1: "t", 4: "m", 22: "s", 6: "v", 3: "f"
        }# }}}
        results = []
        for item in rsp['result']['items']:# {{{
            #if '•' in item['label']: continue  # dont contain other library function.
            r = {}
            r['word'] = item['insertText']
            r['abbr'] = item['label']
            r['info'] = item['label']
            r['kind'] = kind2type.get(item['kind'], str(item['kind']))
            r['dup'] = 1
            results.append(r)# }}}
        return results
#}}}

def Clangd_GoTo(args, preview=False):# {{{
    """ if preview is True, open in preview windows.
    """
    support_filetype = ['cc', 'h', 'cpp']
    cur_file = osp.abspath(vim_utils.CurrentEditFile())
    suffix =  cur_file.split(".")[-1]
    if suffix not in support_filetype:
        print("Not a cpp file")
        return []

    position = vim_utils.GetCursorXY()
    #print (position)
    position = position[0]-1, position[1]-1
    if args[0] == 'def': 
        rsp = clangd.goto_def(cur_file, position)
    elif args[0] == 'ref': 
        rsp = clangd.goto_ref(cur_file, position)
    if rsp is None:
        vim_utils.info ("Compiling, Try later.")
        return []
    #print (rsp)
    all_locs = _clangd_to_location( rsp['result'] )
    if len(all_locs) == 0: 
        print ("Implementation No Found !")
        return []
    if preview: 
        GlobalPreviewWindow.set_locs(all_locs)
        GlobalPreviewWindow.show()
    else:
        if len(all_locs) == 1:
            first_loc = all_locs[0]
            vim_utils.GoToLocation(first_loc, '.')
        else: 
            vim_utils.SetQuickFixList(all_locs, True, False)
    return all_locs# }}}

@vim_register(name="GoToDefinition", command="Def")
def Clangd_GoToDef(args):# {{{
    file = vim_utils.CurrentEditFile()
    if file.split('.')[-1] == 'py': vim.command('YcmCompleter GoToDefinition')
    else: Clangd_GoTo(['def'])# }}}

@vim_register(name="GoToReference", command="Ref")
def Clangd_GoToRef(args):# {{{
    Clangd_GoTo(['ref'])# }}}

@vim_register(name="ClangdServerStart")
def ClangdStart(args):# {{{
    send_by_python(cmd='create', directory=do_path_map(vim_utils.GetPwd(), "vim", "clangd"))
    global clangd
    if not clangd: clangd = Clangd()# }}}

@vim_register(name="ClangdServerExit")
def ClangdExit(args):# {{{
    clangd = None
    send_by_python(cmd='remove', directory=do_path_map(vim_utils.GetPwd(), "vim", "clangd"))# }}}

@vim_register(name="ClangdDidOpen")
def ClangdDidOpen(files):# {{{
    if not clangd: ClangdStart([])
    for file in files: 
        clangd.did_open(file)# }}}

@vim_register(name="ClangdServerRestart", command="ClangdRestart")
def ClangdRestart(args):# {{{
    send_by_python(cmd='restart', directory=do_path_map(vim_utils.GetPwd(), "vim", "clangd"))
    global clangd
    clangd = None
    ClangdStart([])# }}}

@vim_register(name="ClangdServerReparse")
def ClangdReparseCurFile(args):
    if clangd: clangd.reparse_currentfile()

@vim_register(name="ClangdServerDiags", command="Compile")
def ClangdGetDiags(args):
    if clangd: 
        clangd.reparse_currentfile(True) # make sure file is the newest.
        time.sleep(0.5)
        clangd.get_diagnostics(vim_utils.CurrentEditFile(True))

@vim_register(name="ClangdServerComplete1", command="CP")
def ClangdCompleteInterface(args):# {{{
    support_filetype = ['cc', 'h', 'cpp']
    cur_file = osp.abspath(vim_utils.CurrentEditFile())
    suffix =  cur_file.split(".")[-1]
    if suffix not in support_filetype:
        print("Not a cpp file")
        return []
    position = vim_utils.GetCursorXY()
    position = position[0]-1, position[1]-1
    clangd.reparse_currentfile(True) # make sure file is the newest.
    time.sleep(0.3)
    return clangd.complete(cur_file, position)
# }}}

def uri2abspath(uri):
    return do_path_map(uri[7:], "clangd", "vim")

@vim_register(name="ClangdServerComplete")
def ClangdComplete(args):# {{{
    """
    {'isIncomplete': False, 'items': [{'filterText': 'MyClass', 'insertText': 'MyClass', 'insertTextFormat': 1, 'kind': 7, 'label': ' MyClass', 'score': 2.0423638820648193, 'sortText': '3ffd49e9MyClass', 'textEdit': {'newText': 'MyClass', 'range': {'end': {'character': 10, 'line': 16}, 'start': {'character': 4, 'line': 16}} } }]}
    """
    def find_start_pos():# {{{
        line = vim_utils.GetCurrentLine()
        col = vim_utils.GetCursorXY()[1] - 2 # 1-base -> 0-base
        while col >= 0 and (col >= len(line) or line[col].isalpha() or line[col] in ['_']):
            col -= 1
        return col + 2  # 1 for offset, 2 for 1-base}}}
    if clangd:
        l = ClangdCompleteInterface(args)
        vim_l = vim_utils.VimVariable().assign(l)
        vim.eval('complete(%d, %s)' % (find_start_pos(), vim_l))# }}}

@vim_register(name="ClangdClose", command="ClangdStop")
def ClangdClose(args):# {{{
    if clangd:
        _EndAutoCompile()

def _clangd_to_location(result):# {{{
    loc = []
    for r in result:
        loc.append(vim_utils.Location(uri2abspath(r['uri']), r['range']['start']['line']+1, r['range']['start']['character']+1))
    return loc# }}}
