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
import traceback
import os
import sys

def Singleton(cls):
    instance = None
    def get_instance():
        nonlocal instance
        if instance is None: 
            instance = cls()
        return instance
    return get_instance


def pack(package):
    bytes = json.dumps(package)
    package = f"Content-Length: {len(bytes)}\r\n\r\n" + bytes
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

class LSPProxy:
    def __init__(self):
        self.server_candidate = [JediServer(), ClangdServer()]
        self.version_map = {}
        self.rootUri = ""
        self.is_init = False

    def getFds(self):
        ret = []
        for server in self.server_candidate:
            fd = server.get_output_fd()
            if fd is not None: ret.append(fd)
        return ret

    def updateVersion(self, filepath, content):
        strings = "\n".join(content)
        if filepath not in self.version_map:
            self.version_map[filepath] = (1, hash(strings))
        else:
            cnt, hash_id = self.version_map[filepath]
            if hash(strings) != hash_id: 
                self.version_map[filepath] = (cnt+1, hash(strings))
        return self.lastest(filepath)

    def file_exist(self, filepath):
        return filepath in self.version_map

    def lastest(self, filepath):
        return self.version_map[filepath][0]

    def complete_resolve(self, id, filepath, complete_item):
        json = {
            "jsonrpc": "2.0",
            "id": id,
            "method": "completionItem/resolve",
            "params": complete_item,
        }
        self.dispatch(filepath, json)

    # @interface
    def init(self, id, rootUri):
        self.rootUri = rootUri
        self.is_init = True

    # @interface
    def complete(self, id, filepath, pos):
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
                        "uri": "file://" + filepath,
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
        self.dispatch(filepath, json)
        
    #@interface
    def goto(self, id, filepath, method="definition", pos=(0,0)):
        """ definition | implementation
        """
        json = {
            "jsonrpc": "2.0",
            "id": id,
            "method": "textDocument/%s" % method,
            "params": {
                "textDocument": {
                    "uri": "file://" + filepath,
                },
                "position": {
                    "line": pos[0], 
                    "character" : pos[1] 
                }
            }
        }
        self.dispatch(filepath, json)

    #@interface
    def signature_help(self, id, filepath, pos=(0,0)):
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
                    "uri": "file://" + filepath,
                    "version": self.lastest(filepath),
                },
                "position": {
                    "line": pos[0], 
                    "character" : pos[1],
                },
            }
        }
        self.dispatch(filepath, json)

    #@interface
    def did_change(self, id, filepath, content, want_diag=True):
        if not os.path.isfile(filepath): 
            return 
        if not self.file_exist(filepath): 
            self.add_document(-1, filepath)
        def getContentChanges(filepath, content):
            return {
                'range': None, 
                'rangeLength': None,
                'text': content
            }

        param = {
            "textDocument": {
                "uri": "file://" + filepath,
                "version": self.updateVersion(filepath, content),
            },
            "contentChanges": [{"text": "\n".join(content)}],
            "wantDiagnostics": want_diag,
            "forceRebuild": False,
        }
        json = {
            "jsonrpc": "2.0",
            "method": "textDocument/didChange",
            "params": param,
        }
        self.dispatch(filepath, json)

    #@interface
    def add_document(self, id, filepath):
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
                        "uri": "file://" + filepath,
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
            self.dispatch(filepath, json)
        return None

    #@interface
    def dispatch(self, filepath, json):
        print ("[LSP input ] ", json)
        server = self.get_server(filepath)
        server.stdin.write(pack(json))
        server.stdin.flush()

    def get_server(self, filepath):
        suff = filepath.split('.')[-1]
        for s in self.iter_servers():
            if s.match_suffix(suff): 
                s.try_start(self.rootUri)
                return s

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

class LanguageServer: 
    def __init__(self):
        self.is_init = False

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

    def start(self, rootUri):
        import subprocess
        if not self.is_installed(): 
            raise RuntimeError(f"{self.__class__} is not installed")
        self.rootUri = rootUri
        cmd = self.get_command()
        server = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=False)
        server.stdin.write(pack(self.initialize(rootUri)))
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

@Singleton
class JediServer(LanguageServer): 
    def __init__(self):
        super().__init__()

    def initialize(self, rootUri):
        init = '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"capabilities":{"textDocument":{"hover":{"dynamicRegistration":true,"contentFormat":["plaintext","markdown"]},"synchronization":{"dynamicRegistration":true,"willSave":false,"didSave":false,"willSaveWaitUntil":false},"completion":{"dynamicRegistration":true,"completionItem":{"snippetSupport":false,"commitCharactersSupport":true,"documentationFormat":["plaintext","markdown"],"deprecatedSupport":false,"preselectSupport":false},"contextSupport":false},"signatureHelp":{"dynamicRegistration":true,"signatureInformation":{"documentationFormat":["plaintext","markdown"]}},"declaration":{"dynamicRegistration":true,"linkSupport":true},"definition":{"dynamicRegistration":true,"linkSupport":true},"typeDefinition":{"dynamicRegistration":true,"linkSupport":true},"implementation":{"dynamicRegistration":true,"linkSupport":true}},"workspace":{"didChangeConfiguration":{"dynamicRegistration":true}}},"initializationOptions":null,"processId":null,"rootUri":"file:///home/ubuntu/artifacts/","workspaceFolders":null}}'
        return json.loads(init)

    def match_suffix(self, suf):
        return suf == 'py'

    def getLanguageId(self):
        return "python"

    def executable(self):
        return "jedi-language-server"

    def get_command(self):
        cmd = [f'cd {self.rootUri} && jedi-language-server 2>jedi.log']
        return cmd

@Singleton
class ClangdServer(LanguageServer): 
    def __init__(self):
        super().__init__()

    def initialize(self, rootUri):
        init = '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"capabilities":{"textDocument":{"hover":{"dynamicRegistration":true,"contentFormat":["plaintext","markdown"]},"synchronization":{"dynamicRegistration":true,"willSave":false,"didSave":false,"willSaveWaitUntil":false},"completion":{"dynamicRegistration":true,"completionItem":{"snippetSupport":false,"commitCharactersSupport":true,"documentationFormat":["plaintext","markdown"],"deprecatedSupport":false,"preselectSupport":false},"contextSupport":false},"signatureHelp":{"dynamicRegistration":true,"signatureInformation":{"documentationFormat":["plaintext","markdown"]}},"declaration":{"dynamicRegistration":true,"linkSupport":true},"definition":{"dynamicRegistration":true,"linkSupport":true},"typeDefinition":{"dynamicRegistration":true,"linkSupport":true},"implementation":{"dynamicRegistration":true,"linkSupport":true}},"workspace":{"didChangeConfiguration":{"dynamicRegistration":true}}},"initializationOptions":null,"processId":null,"rootUri":null,"workspaceFolders":null}}'
        package = json.loads(init)
        package['params']['rootUri'] = rootUri
        return package

    def match_suffix(self, suf):
        return suf in ['cc', 'h', 'cpp', 'hpp', 'cu']

    def getLanguageId(self):
        return "cpp"

    def executable(self):
        return "clangd"

    def get_command(self):
        return [f'cd {self.rootUri} && clangd 2>clangd.log']

def handle_input(handle, lsp, req):
    try:
        id = req[0]
        func = getattr(lsp, req[1])
        if req[1] != "init" and not lsp.is_init: 
            raise RuntimeError("Please call lsp init first.")
        func(id, *req[2])
    except Exception as e:
        print ("[LSP] error: ", e)
        traceback.print_exc()
        send_to_vim(handle, Protocal.CreateShowMessage(1, f"{str(e)}"))

def receive_package(r):
    size = int(r.readline().strip().split(b':')[1])
    while True:
        line = r.readline().strip()
        if not line: break
    output = r.read(size).decode("utf-8")
    print ("[LSP output]", output)
    try:
        return json.loads(output)
    except: 
        breakpoint() 
        a = 0

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

def lsp_server(handle):
    lsp_proxy = LSPProxy()
    stream = SockStream()
    exit = False
    while not exit:
        rfds = lsp_proxy.getFds()
        sys.stdout.flush()
        rs, ws, es = select.select(rfds + [handle.rfile.fileno()], [], [], 1.0)
        for r in rs:
            if r in [handle.rfile.fileno()]:
                try:
                    bytes = handle.request.recv(10240)
                except socket.error:
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

    # exit bash or killed.
    print ("[LSP] exit bash server.")
    print("=== socket closed ===")

if __name__ == "__main__":
    pass