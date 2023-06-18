import os
import sys
import select
import termios
import tty
import pty
import subprocess
import socket
import json

class LSPManager:
    def __init__(self):
        self.servers = []
        self.file2server = {}
        pass

    def getServer(self, filepath):
        pass
    
    def register(self, suffix, func):
        pass

    def getFds (self): 
        rfds = [s.rfd() for s in self.servers]
        return rfds

manager = LSPManager()

class Server(self):
    def __init__(self):
        pass

    def rfd (self):
        pass

def handle_input(handle):
    bytes = handle.rfile.readline()
    if not bytes: 
        slave_process.kill()
        break
    bytes = bytes.strip()
    pack = json.loads(bytes.decode('utf-8'))
    if pack['type'] == 'input': 
        os.write(master_fd, pack['body'].encode('utf-8'))
    elif pack['type'] == 'keeplive': 
        #print ("heart beat got.")
        pass

def handle_lsp_input(r):
    bytes = os.read(r, 10240)
    handle.wfile.write(bytes)

def lsp_server(handle):
    rfds = manager.getFds()
    rs, ws, es = select.select(rfds + [handle.rfile.fileno()], [], [])
    for r in rs:
        if r in [handle.rfile.fileno()]:
            handle_input(handle)
        else:
            handle_lsp_input(r)
    # exit bash or killed.
    print ("[LSP] exit bash server.")
    print("=== socket closed ===")

