# -*- coding: utf-8 -*-
import os
import sys
import select
import termios
import tty
import pty
from subprocess import Popen
import socket
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

old_tty = termios.tcgetattr(sys.stdin)
tty.setraw(sys.stdin.fileno())
while True: 
    r, w, e = select.select([sys.stdin, sock], [], [])
    if sys.stdin in r:
        inputs = os.read(sys.stdin.fileno(), 10240)
        sock.send(inputs)
    elif sock in r:
        outputs = sock.recv(10240)
        if outputs: os.write(sys.stdout.fileno(), outputs)
        else: break

termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
print ("Exit Remote Bash. thanks: @xiongkun")
