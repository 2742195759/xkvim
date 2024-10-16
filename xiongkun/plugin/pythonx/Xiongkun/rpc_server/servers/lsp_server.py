import select
import termios
import tty
import pty
import subprocess
import socket
import json
import time
import requests  
from socket_stream import SockStream
from collections import namedtuple
import traceback
import os
import sys

class DisableException(Exception):
    pass

def pack(package):
    bytes = json.dumps(package)
    package = f"Content-Length: {len(bytes)}\r\n\r\n" + bytes
    print ("[LSP input ] ", package.encode("utf-8"))
    return package.encode("utf-8")

class Protocal: 
    @classmethod
    def CreateShowMessage(cls, type, message):
        json = {
            'method': 'window/showMessage',
            'params': {
                'type': type,
                'message': message,
            }
        }
        return json

    @classmethod
    def CreateDummyResult(cls, id):
        json = {
            "jsonrpc": "2.0",
            "id": id,
            "result": None
        }
        return json

    @classmethod
    def InitializedNotification(cls):
        json = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        return json

class FileRequestQueue:
    def __init__(self):
        self.file2queue = {}
        self.server = None
        self.handle = None

    def set_server_and_handle(self,server, handle):
        self.server = server
        self.handle = handle

    def optimize(self, filepath, req_array):
        # optimize version quest.
        # if version_id != current_version: skip this request.
        def is_version_valid(req):
            if req.get("method", None) == "textDocument/didChange": return True # didChange send delta, should always send to client.
            version = req.get("params", {}).get("textDocument", {}).get("version", None)
            if version is None: return True
            return self.server.lastest(filepath) == version

        ret = []
        for req in req_array: 
            if is_version_valid(req): ret.append(req)
            else: 
                if 'id' in req: 
                    print("[skip request]", req)
                    send_to_vim(self.handle, Protocal.CreateDummyResult(req['id']))
                else: 
                    print("[skip notification]", req)
        return ret

    def pend_request(self, filepath, req): 
        if filepath not in self.file2queue: 
            self.file2queue[filepath] = []
        self.file2queue[filepath].append(req)
        self.file2queue[filepath] = self.optimize(filepath, self.file2queue[filepath])

    def do_request(self):
        for file, reqs in self.file2queue.items():
            for req in reqs:
                try:
                    self.server._dispatch(file, req)
                except:
                    pass
        self.file2queue = {}

def uri_file(file):
    return "file://" + file

class LSPProxy:
    def __init__(self, queue):
        self.server_candidate = []
        self.version_map = {}
        self.disable_filetype = []
        self.rootUri = ""
        self.is_init = False
        self.queue = queue

    def getFds(self):
        ret = []
        for server in self.server_candidate:
            fd = server.get_output_fd()
            if fd is not None: ret.append(fd)
        return ret

    def check_disable(self, filepath):
        if filepath.split('.')[-1] in self.disable_filetype: 
            raise DisableException()

    def updateVersion(self, filepath, content):
        if filepath not in self.version_map:
            self.version_map[filepath] = (0, hash(0))
        else: 
            cnt, hash_id = self.version_map[filepath]
            self.version_map[filepath] = (cnt+1, hash(cnt+1))
        return self.lastest(filepath)

    def file_exist(self, filepath):
        return filepath in self.version_map

    def lastest(self, filepath):
        return self.version_map[filepath][0]

    def complete_resolve(self, id, filepath, complete_item):
        if not self.get_server(filepath).has_complete_resolve(): 
            raise DisableException()
        json = {
            "jsonrpc": "2.0",
            "id": id,
            "method": "completionItem/resolve",
            "params": complete_item,
        }
        self.pending(filepath, json)

    # @interface
    def init(self, id, json_config):
        self.config = json_config
        self.rootUri = self.config["rootUri"]
        for name, server_config in self.config['servers'].items():
            print ("Append: ", name, server_config)
            self.server_candidate.append(ConfigurableServer(name, server_config))
        self.is_init = True

    # @interface
    def disable_file(self, id, suffix): # disable_file cu
        self.disable_filetype.append(suffix)

    # @interface
    def cancel(self, id, filepath, to_cancel):
        json = {
            "jsonrpc": "2.0",
            "method": "$/cancelRequest",
            "params": {
                "id": to_cancel
            }
        }
        self.dealing(filepath, json)

    # @interface
    def complete(self, id, filepath, pos):
        self.check_disable(filepath)
        def lsp_complete(id, filepath, pos=(0,0)):
            json = {
                "jsonrpc": "2.0",
                "id": id,
                "method": "textDocument/completion",
                "params": {
                    "context": {
                        "triggerKind": 1, # invoke trigger.
                    },
                    "textDocument": {
                        "uri": uri_file(filepath),
                        "version": self.lastest(filepath),
                    },
                    "position": {
                        "line": pos[0], 
                        "character" : pos[1],
                    },
                }
            }
            return json
        json = lsp_complete(id, filepath, pos)
        self.pending(filepath, json)
        
    #@interface
    def goto(self, id, filepath, method="definition", pos=(0,0)):
        if not self.get_server(filepath).has_definition_provider(): 
            raise DisableException()
        self.check_disable(filepath)
        if not self.file_exist(filepath): 
            self.add_document(-1, filepath)
        """ definition | implementation | reference
        """
        json = {
            "jsonrpc": "2.0",
            "id": id,
            "method": "textDocument/%s" % method,
            "params": {
                "textDocument": {
                    "uri": uri_file(filepath)
                },
                "position": {
                    "line": pos[0], 
                    "character" : pos[1] 
                }
            }
        }
        self.pending(filepath, json)

    #@interface
    def signature_help(self, id, filepath, pos=(0,0)):
        if not self.get_server(filepath).has_signature_help(): 
            raise DisableException()
        self.check_disable(filepath)
        json = {
            "jsonrpc": "2.0",
            "id": id,
            "method": "textDocument/signatureHelp",
            "params": {
                "context": {
                    "triggerKind": 1, # invoke trigger.
                    "isRetrigger": False,
                },
                "textDocument": {
                    "uri": uri_file(filepath),
                    "version": self.lastest(filepath),
                },
                "position": {
                    "line": pos[0], 
                    "character" : pos[1],
                },
            }
        }
        self.pending(filepath, json)

    #@interface
    def did_change(self, id, filepath, content, want_diag=True):
        """ 
        content: string of lines | delta contentChanges
        """
        self.check_disable(filepath)
        if not os.path.isfile(filepath): 
            return 
        if not self.file_exist(filepath): 
            self.add_document(-1, filepath)
        param = {
            "textDocument": {
                "uri": uri_file(filepath),
                "version": self.updateVersion(filepath, content),
            },
            "contentChanges": None,
            "wantDiagnostics": want_diag,
            "forceRebuild": False,
        }
        if len(content)==0 or isinstance(content[0], dict): 
            param['contentChanges'] = content
        elif isinstance(content[0], str): 
            param['contentChanges'] = [{"text": "\n".join(content)}]

        json = {
            "jsonrpc": "2.0",
            "method": "textDocument/didChange",
            "params": param,
        }
        self.pending(filepath, json)

    #@interface
    def add_document(self, id, filepath):
        self.check_disable(filepath)
        if not os.path.isfile(filepath): 
            return 
        def _add_document(filepath, languageId):
            with open(filepath, 'r') as fp:
                content = fp.readlines()
            json = {
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": uri_file(filepath),
                        "languageId": languageId,
                        "version": self.updateVersion(filepath, content),
                        "text": "".join(content),
                    },
                }
            }
            return json

        if filepath and not self.file_exist(filepath):
            server = self.get_server(filepath)
            json = _add_document(filepath, server.getLanguageId())
            self._dispatch(filepath, json)
        return None

    #@interface
    def _dispatch(self, filepath, json):
        server = self.get_server(filepath)
        server.stdin.write(pack(json))
        server.stdin.flush()
        server.stdout.flush()

    def pending(self, filepath, json):
        self.queue.pend_request(filepath, json)

    def dealing(self, filepath=None, json=None):
        if filepath is not None and json is not None: 
            self.pending(filepath, json)
        self.queue.do_request()

    def get_server(self, filepath):
        self.check_disable(filepath)
        suff = filepath.split('.')[-1]
        for s in self.iter_servers():
            if s.match_suffix(suff): 
                s.try_start(self.rootUri)
                return s
        self.disable_file(-1, suff)
        raise RuntimeError("no server for suffix %s" % suff)

    def iter_servers(self):
        for server in self.server_candidate:
            yield server

    def close(self):
        for server in self.iter_servers():
            if server.is_init:
                server.kill()

    def keeplive(self, id): 
        pass

    # @interface
    def echo(self, id, package): 
        return send_to_vim(self.queue.handle, {'id': id, 'result': package})

class LanguageServer: 
    def __init__(self):
        self.is_init = False
        assert 'HOME' in os.environ, "Home not in os.environment"
        self.home = os.environ['HOME']

    def set_process(self, server):
        self.server = server
        self.stdin = server.stdin
        self.stdout = server.stdout
        self.stderr = server.stderr
        self.is_init = False

    def is_installed(self):
        print (f"which {self.executable()}")
        return os.system(f"which {self.executable()}") == 0

    def kill(self):
        self.server.kill()

    def do_install(self):
        pass

    def start(self, rootUri):
        import subprocess
        if not self.is_installed(): 
            self.do_install()
            if not self.is_installed(): 
                raise RuntimeError(f"{self.__class__} is not installed")
        self.rootUri = rootUri
        cmd = self.get_command()
        print("lsp server start cmd: ", cmd)
        server = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=False)
        server.stdin.write(pack(self.initialize(rootUri)))
        server.stdin.flush()
        init_result = receive_package(server.stdout)
        self.init_result = init_result
        server.stdin.write(pack(Protocal.InitializedNotification()))
        server.stdin.flush()
        self.set_process(server)
        self.is_init = True
        return self

    def try_start(self, *args, **kwargs):
        if not self.is_init: 
            self.start(*args, **kwargs)

    def get_output_fd(self):
        if not self.is_init: return None
        return self.server.stdout

class ConfigurableServer(LanguageServer):
    def __init__(self, name, config):
        super().__init__()
        self.config = config
        self.name = name

    def has_definition_provider(self):
        try:
            return self.init_result['result']['capabilities']['definitionProvider']
        except KeyError:
            return False

    def has_complete_resolve(self):
        try:
            return self.init_result['result']['capabilities']['completionProvider']['resolveProvider']
            #return self.init_result['result']['capabilities']['completionProvider']['resolveSupport']
        except KeyError:
            return False

    def has_signature_help(self):
        try:
            return self.init_result['result']['capabilities']['signatureHelpProvider']
        except KeyError:
            return False

    def initialize(self, rootUri):
        init = '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"capabilities":{"textDocument":{"hover":{"dynamicRegistration":true,"contentFormat":["plaintext","markdown"]},"synchronization":{"dynamicRegistration":true,"willSave":false,"didSave":false,"willSaveWaitUntil":false},"completion":{"dynamicRegistration":true,"completionItem":{"snippetSupport":false,"commitCharactersSupport":true,"documentationFormat":["plaintext","markdown"],"deprecatedSupport":false,"preselectSupport":false},"contextSupport":false},"signatureHelp":{"dynamicRegistration":true,"signatureInformation":{"documentationFormat":["plaintext","markdown"]}},"declaration":{"dynamicRegistration":true,"linkSupport":true},"definition":{"dynamicRegistration":true,"linkSupport":true},"typeDefinition":{"dynamicRegistration":true,"linkSupport":true},"implementation":{"dynamicRegistration":true,"linkSupport":true}},"workspace":{"didChangeConfiguration":{"dynamicRegistration":true}}},"initializationOptions":null,"processId":null,"rootUri":"file:///home/ubuntu/artifacts/","workspaceFolders":null}}'
        init = json.loads(init)
        init['params']['rootUri'] = uri_file(rootUri)
        init_options = self.config.get("initializationOptions", None)
        if init_options is not None: 
            init_options = {
                k: self.dequote(v) 
                for k, v in init_options.items() if isinstance(v, str)
            }
        init['params']['initializationOptions']  = init_options
        return init

    def match_suffix(self, suf):
        filetypes = self.config.get("filetype", [])
        for ft in filetypes: 
            if suf == ft: return True
        return False

    def do_install(self):
        install_cmd = self.config.get("install", None)
        if install_cmd is None: raise RuntimeError(f"can't install {self.name}, because not config `install`")
        install_cmd = self.dequote(install_cmd)
        os.system(install_cmd)

    def getLanguageId(self):
        lid = self.config.get("languageId", None)
        if lid is None: raise RuntimeError("Please set languageId in config")
        return lid

    def executable(self):
        executable = self.config.get("executable", None)
        if executable is None: raise RuntimeError("Please set executable in config")
        return executable

    def dequote(self, abbre):
        assert isinstance(abbre, str)
        idx = 0
        result = []
        while idx < len(abbre): 
            # 分割字符串 abbre 中的 {和 }两个字符中间的部分，使用python执行
            # 例如： abbre = "print({a})"
            python_stmt = []
            while idx < len(abbre) and abbre[idx] != "{":
                if idx + 1 < len(abbre) and abbre[idx:idx+2] == "}}":
                    result.append('}')
                    idx += 2
                    continue
                result.append(abbre[idx])
                idx += 1
            if idx + 1 < len(abbre) and abbre[idx+1] == "{":
                result.append('{')
                idx += 2
                continue
            if idx >= len(abbre): continue
            start_stmt = idx
            while idx < len(abbre) and abbre[idx] != "}": 
                idx += 1
            if idx >= len(abbre): raise RuntimeError("{stmt} not match.")
            python_stmt = abbre[start_stmt+1:idx]
            idx += 1 # skip the }
            result.extend(getattr(self, python_stmt))
            #result.extend(f"!!python_stmt: {python_stmt}!!")
        return "".join(result)

    def get_command(self):
        command = self.config.get("command", None)
        if command is None: raise RuntimeError("Please set command in config")
        command = self.dequote(command)
        cmd = [f'cd {self.rootUri} && {command}']
        return cmd

class JediServer(LanguageServer): 
    def __init__(self):
        super().__init__()

    def initialize(self, rootUri):
        init = '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"capabilities":{"textDocument":{"hover":{"dynamicRegistration":true,"contentFormat":["plaintext","markdown"]},"synchronization":{"dynamicRegistration":true,"willSave":false,"didSave":false,"willSaveWaitUntil":false},"completion":{"dynamicRegistration":true,"completionItem":{"snippetSupport":false,"commitCharactersSupport":true,"documentationFormat":["plaintext","markdown"],"deprecatedSupport":false,"preselectSupport":false},"contextSupport":false},"signatureHelp":{"dynamicRegistration":true,"signatureInformation":{"documentationFormat":["plaintext","markdown"]}},"declaration":{"dynamicRegistration":true,"linkSupport":true},"definition":{"dynamicRegistration":true,"linkSupport":true},"typeDefinition":{"dynamicRegistration":true,"linkSupport":true},"implementation":{"dynamicRegistration":true,"linkSupport":true}},"workspace":{"didChangeConfiguration":{"dynamicRegistration":true}}},"initializationOptions":null,"processId":null,"rootUri":"file:///home/ubuntu/artifacts/","workspaceFolders":null}}'
        init = json.loads(init)
        init['params']['rootUri'] = uri_file(rootUri)
        return init

    def match_suffix(self, suf):
        return suf == 'py'

    def getLanguageId(self):
        return "python"

    def executable(self):
        return "jedi-language-server"

    def get_command(self):
        cmd = [f'cd {self.rootUri} && jedi-language-server 2>jedi.log']
        return cmd

# Wrong Implementation
# Stuch when didchange
class HaskellServer(LanguageServer): 
    def __init__(self):
        super().__init__()

    def initialize(self, rootUri):
        init = '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"capabilities":{"textDocument":{"hover":{"dynamicRegistration":true,"contentFormat":["plaintext","markdown"]},"synchronization":{"dynamicRegistration":true,"willSave":false,"didSave":false,"willSaveWaitUntil":false},"completion":{"dynamicRegistration":true,"completionItem":{"snippetSupport":false,"commitCharactersSupport":true,"documentationFormat":["plaintext","markdown"],"deprecatedSupport":false,"preselectSupport":false},"contextSupport":false},"signatureHelp":{"dynamicRegistration":true,"signatureInformation":{"documentationFormat":["plaintext","markdown"]}},"declaration":{"dynamicRegistration":true,"linkSupport":true},"definition":{"dynamicRegistration":true,"linkSupport":true},"typeDefinition":{"dynamicRegistration":true,"linkSupport":true},"implementation":{"dynamicRegistration":true,"linkSupport":true}},"workspace":{"didChangeConfiguration":{"dynamicRegistration":true}}},"initializationOptions":null,"processId":null,"rootUri":"file:///home/ubuntu/artifacts/","workspaceFolders":null}}'
        init = json.loads(init)
        init['params']['rootUri'] = uri_file(rootUri)
        init['params']['rootPath'] = rootUri
        init['params']['workspaceFolders'] = [{
            'uri': uri_file(rootUri),
            'name': os.path.basename(rootUri),
        }]
        return init

    def match_suffix(self, suf):
        return suf in ['hs']

    def getLanguageId(self):
        return "haskell"

    def executable(self):
        return "haskell-language-server-wrapper"

    def get_command(self):
        cmd = [f'cd {self.rootUri} && haskell-language-server-wrapper -j 5 --debug --cwd {self.rootUri} --lsp 2>haskell.log']
        return cmd

class ClangdServer(LanguageServer): 
    def __init__(self):
        super().__init__()

    def initialize(self, rootUri):
        init = '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"capabilities":{"textDocument":{"hover":{"dynamicRegistration":true,"contentFormat":["plaintext","markdown"]},"synchronization":{"dynamicRegistration":true,"willSave":false,"didSave":false,"willSaveWaitUntil":false},"completion":{"dynamicRegistration":true,"completionItem":{"snippetSupport":false,"commitCharactersSupport":true,"documentationFormat":["plaintext","markdown"],"deprecatedSupport":false,"preselectSupport":false},"contextSupport":false},"signatureHelp":{"dynamicRegistration":true,"signatureInformation":{"documentationFormat":["plaintext","markdown"]}},"declaration":{"dynamicRegistration":true,"linkSupport":true},"definition":{"dynamicRegistration":true,"linkSupport":true},"typeDefinition":{"dynamicRegistration":true,"linkSupport":true},"implementation":{"dynamicRegistration":true,"linkSupport":true}},"workspace":{"didChangeConfiguration":{"dynamicRegistration":true}}},"initializationOptions":null,"processId":null,"rootUri":null,"workspaceFolders":null}}'
        package = json.loads(init)
        package['params']['rootUri'] = uri_file(rootUri)
        return package

    def match_suffix(self, suf):
        return suf in ['cc', 'h', 'cpp', 'hpp', 'c']

    def getLanguageId(self):
        return "cpp"

    def executable(self):
        return "clangd"

    def get_command(self):
        return [f'clangd --background-index=0 --compile-commands-dir={self.rootUri} -j=10 2>clangd.log']

class CMakeServer(LanguageServer): 
    def __init__(self):
        super().__init__()

    def initialize(self, rootUri):
        init = '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"capabilities":{"textDocument":{"hover":{"dynamicRegistration":true,"contentFormat":["plaintext","markdown"]},"synchronization":{"dynamicRegistration":true,"willSave":false,"didSave":false,"willSaveWaitUntil":false},"completion":{"dynamicRegistration":true,"completionItem":{"snippetSupport":false,"commitCharactersSupport":true,"documentationFormat":["plaintext","markdown"],"deprecatedSupport":false,"preselectSupport":false},"contextSupport":false},"signatureHelp":{"dynamicRegistration":true,"signatureInformation":{"documentationFormat":["plaintext","markdown"]}},"declaration":{"dynamicRegistration":true,"linkSupport":true},"definition":{"dynamicRegistration":true,"linkSupport":true},"typeDefinition":{"dynamicRegistration":true,"linkSupport":true},"implementation":{"dynamicRegistration":true,"linkSupport":true}},"workspace":{"didChangeConfiguration":{"dynamicRegistration":true}}},"initializationOptions":null,"processId":null,"rootUri":null,"workspaceFolders":null}}'
        package = json.loads(init)
        package['params']['rootUri'] = uri_file(os.path.join(rootUri, "build"))
        package['params']['initializationOptions'] = {"buildDirectory": uri_file(os.path.join(rootUri, "build"))}
        return package

    def match_suffix(self, suf):
        return suf in ['cmake']

    def getLanguageId(self):
        return "cmake"

    def executable(self):
        return "cmake-language-server"

    def get_command(self):
        return [f'cmake-language-server --background-index=0 --compile-commands-dir={self.rootUri} -j=10 2>clangd.log']

    def install_command(self):
        return "pip install cmake-language-server"


def handle_input(handle, lsp, req):
    try:
        id = req[0]
        func = getattr(lsp, req[1])
        if req[1] != "init" and not lsp.is_init: 
            raise RuntimeError("Please call lsp init first.")
        func(id, *req[2])
    except DisableException as e: 
        send_to_vim(handle, {'id': id, 'result': None})
    except Exception as e:
        print ("[LSP] error: ", e)
        traceback.print_exc()
        send_to_vim(handle, Protocal.CreateShowMessage(1, f"{str(e)}"))

def receive_package(r):
    output = r.readline()
    print ("[LSP output leader]", output)
    size = int(output.strip().split(b':')[1])
    while True:
        line = r.readline().strip()
        if not line: break
    output = r.read(size).decode("utf-8")
    print ("[LSP output]", output)
    return json.loads(output)

def is_method(package):
    return "method" in package

def is_response(package):
    return "id" in package

def send_to_vim(handle, package):
    if is_response(package):
        id = int(package["id"])
        handle.wfile.write(json.dumps([id, True, package]).encode('utf-8') + b"\n")
    else: 
        handle.wfile.write(json.dumps([-1, True, package]).encode('utf-8') + b"\n")
    print(f"[SendVim] {package}")

def handle_lsp_output(r, handle):
    package = receive_package(r)
    send_to_vim(handle, package)

def handle_idle(handle, lsp_proxy):
    lsp_proxy.dealing()

def lsp_server(socket, mp_manager):
    Handle = namedtuple("Handle", ['wfile', 'rfile', 'request'])
    rfile = socket.makefile('rb', 10240)
    wfile = socket.makefile('wb', 0)
    handle = Handle(wfile, rfile, socket)
    queue = FileRequestQueue() # for speed up.
    lsp_proxy = LSPProxy(queue)
    queue.set_server_and_handle(lsp_proxy, handle)
    stream = SockStream()
    exit = False
    while not exit:
        rfds = lsp_proxy.getFds()
        sys.stdout.flush()
        sys.stderr.flush()
        rs, ws, es = select.select(rfds + [handle.rfile.fileno()], [], [], 0.3)
        if len(rs) == 0: 
            handle_idle(handle, lsp_proxy)
            continue
        for r in rs:
            if r in [handle.rfile.fileno()]:
                try:
                    bytes = handle.request.recv(10240)
                except:
                    print("=== socket error ===")
                    exit = True

                if bytes == b'':
                    print("=== socket closed ===")
                    exit = True

                stream.put_bytes(bytes)
                while stream.can_read():
                    data = stream.readline().decode('utf-8')
                    print("[FromVim] received: {0}".format(data))
                    try:
                        req = json.loads(data)
                    except ValueError:
                        print("json decoding failed")
                        req = [-1, '']
                    handle_input(handle, lsp_proxy, req)
            else:
                handle_lsp_output(r, handle)
    lsp_proxy.close()
    socket.close()

    # exit bash or killed.
    print ("[LSP] exit lsp server.")
    print("=== socket closed ===")

if __name__ == "__main__":
    pass
