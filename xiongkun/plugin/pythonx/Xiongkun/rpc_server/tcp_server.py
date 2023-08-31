#!/usr/bin/python
#
# Server that will accept connections from a Vim channel.
# Run this server and then in Vim you can open the channel:
#  :let handle = ch_open('localhost:8765')
#
# Then Vim can send requests to the server:
#  :let response = ch_sendexpr(handle, 'hello!')
#
# And you can control Vim by typing a JSON message here, e.g.:
#   ["ex","echo 'hi there'"]
#
# There is no prompt, just type a line and press Enter.
# To exit cleanly type "quit<Enter>".
#
# See ":help channel-demo" in Vim.
#
# This requires Python 2.6 or later.

from __future__ import print_function
import json
import socket
import sys
import threading
from threading import Thread
from server_cluster import ServerCluster
from vimrpc.decorator import InQueue
from servers.bash_server import bash_server
from servers.lsp_server import lsp_server
import select
from socket_stream import SockStream
from log import log
import multiprocessing as mp
import signal
import os

mp_manager = None

# send the signal to the child process.
#def handler(sig, frame):
    #pgid = os.getpgid(0)
    #with open("/tmp/local_vimcode.log", "w") as fp:
        #fp.write(f"Start killing all pgid process: pgid={pgid}")
    #signal.signal(signal.SIGTERM, signal.SIG_DFL)
    #os.killpg(pgid, signal.SIGTERM)
#signal.signal(signal.SIGTERM, handler)

try:
    # Python 3
    import socketserver
except ImportError:
    # Python 2
    import SocketServer as socketserver

def vim_rpc_loop(socket):
    rfile = socket.makefile('rb', 10240)
    wfile = socket.makefile('wb', 10240)
    print ("===== start a vim rpc server ======")
    def send(obj):
        encoded = json.dumps(obj) + "\n"
        wfile.write(encoded.encode('utf-8'))
        wfile.flush()

    servers = ServerCluster(mp_manager)
    servers.start_queue(send)
    stream = SockStream()

    while True:
        rs, ws, es = select.select([rfile.fileno()], [], [], 3.0)
        sys.stdout.flush()
        sys.stderr.flush()
        if rfile.fileno() in rs:
            try:
                bytes = socket.recv(10240)
            except socket.error:
                print("=== socket error ===")
                break
            if bytes == b'':
                print("=== socket closed ===")
                break
            stream.put_bytes(bytes)
            while stream.can_read():
                data = stream.readline().decode('utf-8')
                print("received: {0}".format(data))
                try:
                    req = json.loads(data)
                except ValueError:
                    print("json decoding failed")
                    req = [-1, '']

                # Send a response if the sequence number is positive.
                # Negative numbers are used for "eval" responses.
                if req[0] >= 0:
                    print (req)
                    id, name, args = req
                    print("[Server] receive: ", id, name)
                    func = servers.get_server_fn(name)
                    if not func:
                        continue
                    output = func(id, *args)
                    if isinstance(output, InQueue): 
                        print("[Server]: process function.")
                    else: 
                        print("[Server]: normal function.")
                        send(output)
    print ("stop handle, closing...")
    servers.stop()
    socket.close()
    print ("===== stop a vim rpc server ======")

child_pid = []

class ThreadedTCPServer(socketserver.TCPServer):
    pass

def connection_handle(socket):
    # override the main process signal handler.
    global child_pid
    print("=== socket opened ===")
    mode = b""
    c = socket.recv(1)
    while c != b'\n': # read just one line and don't buffer.
        mode += c
        c = socket.recv(1)
    print ("[TCPServer] receive: ", mode)
    mode = mode.strip()
    if mode == b"bash": 
        proc = mp.Process(target=bash_server, args=(socket, ))
    elif mode == b"vimrpc":
        proc = mp.Process(target=vim_rpc_loop, args=(socket, ))
    elif mode == b"lsp":
        proc = mp.Process(target=lsp_server, args=(socket, ))
    else: 
        print (f"Unknow command. {mode}")
    proc.daemon=False
    proc.start()
    child_pid.append(proc)
    sys.stdout.flush()

def server_tcp_main(HOST, PORT):
    global child_pid
    listen_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_s.bind((HOST, PORT))
    listen_s.listen(5)
    print ("开始监听: ", (HOST, PORT))
    try:
        while True: 
            r, w, e = select.select([listen_s], [], [], 10.0)
            if listen_s in r:
                try:
                    cnn, addr = listen_s.accept()
                    cnn.setsocket(socket.SOL_SOCKET, socket.SO_KEEPALIVE, True) # 设置保活机制
                    cnn.ioctl(socket.SIO_KEEPALIVE_VALS,  
                        (1,  # open
                        60*1000, # 1 min/ send keepalive
                        30*1000))# 30s interval,10 times.
                    connection_handle(cnn)
                    cnn.close() # close in this process.
                except ConnectionResetError:
                    cnn.close()
                    break
            print (f"Joining Child Processes... [{len(child_pid)}]")
            for proc in child_pid:
                proc.join(0.2)
            child_pid = [ proc for proc in child_pid if proc.exitcode is None ] # None means not exit.
    except: 
        raise
    finally:
        print ("Killing and Joining Child Processes...")
        for proc in child_pid:
            proc.terminate()
            proc.join()
        print ("Exit succesfully.")

def parameter_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Support Args:")

    parser.add_argument("--host",                      type=str,   help="127.0.0.1")
    parser.add_argument("--port",                      type=str,   help="8080")
    return parser.parse_args()

if __name__ == "__main__":
    mp.set_start_method("fork")
    mp_manager = mp.Manager()
    args = parameter_parser()
    server_tcp_main(args.host, int(args.port))
