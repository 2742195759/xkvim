import os
import sys
import select
import termios
import tty
import pty
import subprocess
import socket
import json

command = 'bash'

def start_config(handle):
    config = json.loads(handle.rfile.readline().strip())
    #config['pwd']
    #return "PWD={} bash"

def bash_server(handle):
    print ("[Bash] start bash server.")
    #command = start_config(handle)
    master_fd, slave_fd = pty.openpty()
    # use os.setsid() make it run in a new process group, or bash job control will not be enabled
    slave_process = subprocess.Popen(command,
              preexec_fn=os.setsid,
              stdin=slave_fd,
              stdout=slave_fd,
              stderr=slave_fd,
              universal_newlines=True)

    while slave_process.poll() is None:
        rs, ws, es = select.select([master_fd, handle.rfile.fileno()], [], [])
        for r in rs:
            if r in [handle.rfile.fileno()]:
                bytes = handle.rfile.readline()
                if not bytes: 
                    slave_process.kill()
                    break
                bytes = bytes.strip()
                pack = json.loads(bytes.decode('utf-8'))
                if pack['type'] == 'input': 
                    os.write(master_fd, pack['body'].encode('utf-8'))
                elif pack['type'] == 'keeplive': 
                    pass
            elif r in [master_fd]:
                bytes = os.read(r, 10240)
                handle.wfile.write(bytes)

    # exit bash or killed.
    print ("[Bash] exit bash server.")
    print("=== socket closed ===")
