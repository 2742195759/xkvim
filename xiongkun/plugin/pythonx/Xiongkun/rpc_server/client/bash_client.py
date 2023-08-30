# -*- coding: utf-8 -*-
import os
import sys
import select
import termios
import tty
import pty
from subprocess import Popen
import socket
import json

def parameter_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Support Args:")
    parser.add_argument("--host",                 type=str,   help="data path")
    parser.add_argument("--port",                 type=int,   help="data path")
    return parser.parse_args()

args = parameter_parser()
ip_port = (args.host, args.port)
sock = socket.socket()
sock.connect(ip_port)
sock.send(b"bash\n") # send bash to start bash serve mode.

def create_package(body):
    package = {}
    package['type'] = 'input'
    package['body'] = body.decode("utf-8")
    return json.dumps(package).encode("utf-8") + b'\n'

def create_keeplive():
    package = {}
    package['type'] = 'keeplive'
    package['body'] = ''
    return json.dumps(package).encode("utf-8") + b'\n'

old_tty = termios.tcgetattr(sys.stdin)
tty.setraw(sys.stdin.fileno())
while True: 
    ppid = os.getppid()
    if ppid == 1: break # father process is killed, we exit.
    r, w, e = select.select([sys.stdin, sock], [], [], 3.0)
    if sys.stdin in r:
        inputs = os.read(sys.stdin.fileno(), 10240)
        sock.send(create_package(inputs))
    elif sock in r:
        outputs = sock.recv(10240)
        if outputs: os.write(sys.stdout.fileno(), outputs)
        else: break
    sock.send(create_keeplive())

termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
print ("Exit Remote Bash. thanks: @xiongkun")
