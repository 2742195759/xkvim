import os
import sys
import select
import termios
import tty
import pty
import subprocess
import socket
import json
from collections import namedtuple

command = 'bash'

# Created in Main Process: 
#   session_id -> [ BashProc1, BashProc2, ... ] # GlobalProcess
# 
# Created in Bash Server: 
#   bash_server ( ctl_socket, bash_process )
#   we just create a pipeline between them.

class NamedBashPool: 
    def __init__(self):
        self.pool = {}

    def clear(self):
        pass

    def delete(self, name):
        if name not in self.pool:
            return
        (slave_process, master_fd) = self.pool[name] 
        slave_process.kill()
        slave_process.wait()
        del self.pool[name]

    def names(self):
        return list(self.pool.keys())

    def get_bash_worker(self, name):
        if name not in self.pool:
            master_fd, slave_fd = pty.openpty()
            # use os.setsid() make it run in a new process group, or bash job control will not be enabled
            slave_process = subprocess.Popen(command,
                      preexec_fn=os.setsid,
                      stdin=slave_fd,
                      stdout=slave_fd,
                      stderr=slave_fd,
                      universal_newlines=True)
            self.pool[name] = (slave_process, master_fd)
        proc, master_fd = self.pool[name]
        if proc.poll() is not None:
            del self.pool[name] # clear
        return (proc, master_fd)

def reconnect_bash(socket, master_fd):
    Handle = namedtuple("Handle", ['wfile', 'rfile', 'request'])
    rfile = socket.makefile('rb', 10240)
    wfile = socket.makefile('wb', 0)
    handle = Handle(wfile, rfile, socket)
    print ("[BashPool] start bash server.")
    need_exit = 0
    while need_exit == 0:
        rs, ws, es = select.select([master_fd, handle.rfile.fileno()], [], [])
        for r in rs:
            if r in [handle.rfile.fileno()]:
                bytes = handle.rfile.readline()
                if not bytes: 
                    need_exit = 1
                    break
                bytes = bytes.strip()
                pack = json.loads(bytes.decode('utf-8'))
                if pack['type'] == 'input': 
                    os.write(master_fd, pack['body'].encode('utf-8'))
                elif pack['type'] == 'keeplive': 
                    pass
            elif r in [master_fd]:
                bytes = os.read(r, 10240)
                #print ("[master->handle]", bytes)
                handle.wfile.write(bytes)

    # exit bash or killed.
    handle.wfile.flush()
    rfile.close()
    wfile.close()
    socket.close()
    print ("[BashPool] Connection breaked.")

