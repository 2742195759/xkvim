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
import select

try:
    # Python 3
    import socketserver
except ImportError:
    # Python 2
    import SocketServer as socketserver

def vim_rpc_loop(handle):
    print ("===== start a vim rpc server ======")
    def send(obj):
        encoded = json.dumps(obj) + "\n"
        print("sending {0}".format(encoded))
        handle.wfile.write(encoded.encode('utf-8'))

    servers = ServerCluster()
    servers.start_queue(send)

    while True:
        rs, ws, es = select.select([handle.rfile.fileno()], [], [], 3.0)
        if handle.rfile.fileno() in rs:
            try:
                data = handle.rfile.readline().decode('utf-8')
            except socket.error:
                print("=== socket error ===")
                break
            if data == '':
                print("=== socket closed ===")
                break
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
        else: 
            # heart beat send !
            #print('send heart beat.')
            send([0, True, None])
    print ("stop handle, closing...")
    servers.stop()
    print ("===== stop a vim rpc server ======")

class ThreadedTCPRequestHandler(socketserver.StreamRequestHandler):
    def handle(self):
        print("=== socket opened ===")
        mode = self.rfile.readline()
        mode = mode.strip()
        if mode == b"bash": 
            bash_server(self)
        elif mode == b"vimrpc":
            vim_rpc_loop(self)
        else: 
            print (f"Unknow command. {mode}")

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

def server_tcp_main(HOST, PORT):
    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    ip, port = server.server_address
    server.serve_forever()

def parameter_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Support Args:")

    parser.add_argument("--host",                      type=str,   help="127.0.0.1")
    parser.add_argument("--port",                      type=str,   help="8080")
    return parser.parse_args()

args = parameter_parser()
server_tcp_main(args.host, int(args.port))
