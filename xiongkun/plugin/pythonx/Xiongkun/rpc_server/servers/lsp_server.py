import os
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

def pack(package):
    bytes = json.dumps(package)
    package = f"Content-Length: {len(bytes)}\r\n\r\n" + bytes
    print ("PackageSend: ", package)
    return package.encode('utf-8')

class LSPProxy:
    def __init__(self):
        self.loaded_file = set()
        self.suffix2server = {}
        self.server_candidate = [JediConfig]

    def getFds(self):
        ret = []
        for key, value in self.suffix2server.items():
            ret.append(value.stdout)
        return ret

    #@interface
    def goto(self, id, filepath, method="definition", pos=(0,0)):
        """ definition | implementation
        """
        json = {
            "jsonrpc": "2.0",
            "id": str(id),
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
    def did_change(self, filepath, content, want_diag=True):

        def getContentChanges(self, filepath, content):
            return {
                'range': None, 
                'rangeLength': None,
                'text': content
            }

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
                        "version": 1,
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
        print ("[LSP] ", json)
        server = self.get_server(filepath)
        server.stdin.write(pack(json))

    def get_server(self, filepath):
        suff = filepath.split('.')[-1]
        if suff in self.suffix2server: 
            return self.suffix2server[suff]

        for s in self.server_candidate: 
            if s.match_suffix(suff): 
                server = s.start()
                break

        self.suffix2server[suff] = server
        return server

    def close(self):
        for key, value in self.suffix2server.items():
            value.kill()
        

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
        cmd = ['jedi-language-server ']
        server = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=False)
        server.stdin.write(pack(cls.initialize()))
        return server


def getlanguageId(filepath):
    if filepath.split('.')[-1] == "py":
        return "python"
    if filepath.split('.')[-1] == "cpp":
        return "cpp"

def handle_input(lsp, req):
    id = req[0]
    func = getattr(lsp, req[1])
    func(id, *req[2])
    
def handle_lsp_output(r):
    breakpoint() 
    pass

def lsp_server(handle):
    lsp_proxy = LSPProxy()
    stream = SockStream()
    while True:
        rfds = lsp_proxy.getFds()
        print ("[LSP]", rfds + [handle.rfile.fileno()])
        rs, ws, es = select.select(rfds + [handle.rfile.fileno()], [], [], 1.0)
        print ("[get]", rs)
        for r in rs:
            if r in [handle.rfile.fileno()]:
                try:
                    bytes = handle.request.recv(10240)
                except socket.error:
                    print("=== socket error ===")
                    break
                if bytes == b'':
                    print("=== socket closed ===")
                    break

                stream.put_bytes(bytes)
                while stream.can_read():
                    data = stream.readline().decode('utf-8')
                    print("[LSP] received: {0}".format(data))
                    try:
                        req = json.loads(data)
                    except ValueError:
                        print("json decoding failed")
                        req = [-1, '']
                    handle_input(lsp_proxy, req)
            else:
                handle_lsp_output(r)

    # exit bash or killed.
    print ("[LSP] exit bash server.")
    print("=== socket closed ===")

if __name__ == "__main__":
    lsp = LSPProxy()
    lsp.add_document(1, "/home/xiongkun/test/ttt.py")
    lsp.goto(1, "/home/xiongkun/test/ttt.py", "definition", (5,4))
    server = lsp.suffix2server['py']

    rs, ws, es = select.select([server.stdout], [], [], 1.0)
    print (rs)
    lsp.close()
