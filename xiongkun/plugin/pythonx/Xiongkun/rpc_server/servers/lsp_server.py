import sys
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

def pack(package):
    bytes = json.dumps(package)
    package = f"Content-Length: {len(bytes)}\r\n\r\n" + bytes
    print ("PackageSend: ", package)
    sys.stdout.flush()
    return package

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
        self.loaded_file = set()
        self.suffix2server = {}
        self.server_candidate = [JediConfig]
        self.version_map = {}

    def getFds(self):
        ret = []
        for key, value in self.suffix2server.items():
            ret.append(value.stdout)
        return ret

    def nextVersion(self, filepath):
        if filepath not in self.version_map:
            self.version_map[filepath] = 1
        else:
            self.version_map[filepath] += 1
        return self.version_map[filepath] 

    def lastest(self, filepath):
        return self.version_map[filepath] 

    def complete_resolve(self, id, filepath, complete_item):
        json = {
            "jsonrpc": "2.0",
            "id": id,
            "method": "completionItem/resolve",
            "params": complete_item,
        }
        self.dispatch(filepath, json)

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
    def did_change(self, id, filepath, content, want_diag=True):
        def getContentChanges(filepath, content):
            return {
                'range': None, 
                'rangeLength': None,
                'text': content
            }

        param = {
            "textDocument": {
                "uri": "file://" + filepath,
                "version": self.nextVersion(filepath),
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
        def _add_document(filepath, languageId):
            with open(filepath, 'r') as fp:
                content = fp.readlines()
            content = "".join(content)
            json = {
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": "file://" + filepath,
                        "languageId": languageId,
                        "version": self.nextVersion(filepath),
                        "text": content,
                    },
                }
            }
            return json

        if filepath and filepath not in self.loaded_file:
            server = self.get_server(filepath)
            json = _add_document(filepath, getlanguageId(filepath))
            self.loaded_file.add(filepath)
            self.dispatch(filepath, json)
        return None

    def dispatch(self, filepath, json):
        print ("[LSP input ] ", json)
        server = self.get_server(filepath)
        server.stdin.write(pack(json))
        server.stdin.flush()

    def get_server(self, filepath):
        suff = filepath.split('.')[-1]
        if suff in self.suffix2server: 
            return self.suffix2server[suff]

        server = None
        for s in self.server_candidate: 
            if s.match_suffix(suff): 
                server = s.start()
                break

        if not server:
            raise RuntimeError("no server for suffix %s" % suff)
        self.suffix2server[suff] = server
        return server

    def close(self):
        for key, value in self.suffix2server.items():
            value.kill()

    def keeplive(self, id): 
        pass

class JediConfig: 
    @classmethod
    def initialize(cls):
        init = '{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"capabilities":{"textDocument":{"hover":{"dynamicRegistration":true,"contentFormat":["plaintext","markdown"]},"synchronization":{"dynamicRegistration":true,"willSave":false,"didSave":false,"willSaveWaitUntil":false},"completion":{"dynamicRegistration":true,"completionItem":{"snippetSupport":false,"commitCharactersSupport":true,"documentationFormat":["plaintext","markdown"],"deprecatedSupport":false,"preselectSupport":false},"contextSupport":false},"signatureHelp":{"dynamicRegistration":true,"signatureInformation":{"documentationFormat":["plaintext","markdown"]}},"declaration":{"dynamicRegistration":true,"linkSupport":true},"definition":{"dynamicRegistration":true,"linkSupport":true},"typeDefinition":{"dynamicRegistration":true,"linkSupport":true},"implementation":{"dynamicRegistration":true,"linkSupport":true}},"workspace":{"didChangeConfiguration":{"dynamicRegistration":true}}},"initializationOptions":null,"processId":null,"rootUri":"file:///home/ubuntu/artifacts/","workspaceFolders":null}}'
        return json.loads(init)

    @classmethod
    def match_suffix(cls, suf):
        return suf == 'py'
        
    @classmethod
    def start(cls):
        #os.system("pip install -U jedi-language-server")
        import subprocess
        cmd = ['jedi-language-server 2>log']
        server = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
        server.stdin.write(pack(cls.initialize()))
        return server


def getlanguageId(filepath):
    if filepath.split('.')[-1] == "py":
        return "python"
    if filepath.split('.')[-1] == "cpp":
        return "cpp"


def handle_input(handle, lsp, req):
    try:
        id = req[0]
        func = getattr(lsp, req[1])
        func(id, *req[2])
    except Exception as e:
        print ("[LSP] error: ", e)
        traceback.print_exc()
        send_to_vim(handle, Protocal.CreateShowMessage(1, f"{str(e)}"))

def receive_package(r):
    size = int(r.readline().strip().split(':')[1])
    while True:
        line = r.readline().strip()
        if not line: break
    output = r.read(size)
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
    sys.stdout.flush()

def handle_lsp_output(r, handle):
    package = receive_package(r)
    send_to_vim(handle, package)

def lsp_server(handle):
    lsp_proxy = LSPProxy()
    stream = SockStream()
    exit = False
    while not exit:
        rfds = lsp_proxy.getFds()
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
                    print("[LSP] received: {0}".format(data))
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
    lsp = LSPProxy()
    lsp.add_document(1, "/root/test/ttt.py")
    lsp.goto(2, "/root/test/ttt.py", "definition", (4,4))
    server = lsp.suffix2server['py']

    while True:
        rs, ws, es = select.select([server.stdout], [], [], 1.0)
        if rs : 
            receive_package(rs[0])
    lsp.close()
