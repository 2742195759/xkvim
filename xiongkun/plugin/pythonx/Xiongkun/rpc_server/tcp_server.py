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
from queue_loop import QueueLoop
from queue_loop import QueueLoop
from fuzzy_list import FuzzyList
from file_finder import filefinder
from decorator import InQueue
from remote_fs import remotefs

try:
    # Python 3
    import socketserver
except ImportError:
    # Python 2
    import SocketServer as socketserver

fuzzyfinder = FuzzyList()

def get_server_by_name(name):
    name = name.strip()
    obj = globals()
    for f in name.split('.'): 
        if hasattr(obj, f): 
            obj = getattr(obj, f)
        elif isinstance(obj, dict) and f in obj:
            obj = obj.get(f, None)
        else:
            obj = None
    if callable(obj):
        return obj
    print("[Server]: don't found ", name, ", skip it.")
    return None

class ThreadedTCPRequestHandler(socketserver.StreamRequestHandler):
    def handle(self):
        print("=== socket opened ===")
        def send(obj):
            encoded = json.dumps(obj) + "\n"
            print("sending {0}".format(encoded))
            self.wfile.write(encoded.encode('utf-8'))

        queue_thread = Thread(target=QueueLoop, args=[send], daemon=True).start()
        while True:
            try:
                data = self.rfile.readline().decode('utf-8')
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
                id, name, args = req
                print("[Server] receive: ", id, name)
                func = get_server_by_name(name)
                if not func:
                    continue
                output = func(id, *args)
                if isinstance(output, InQueue): 
                    print("[Server]: process function.")
                else: 
                    print("[Server]: normal function.")
                    send([id, output])

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass

def server_tcp_main(HOST, PORT):
    server = ThreadedTCPServer((HOST, PORT), ThreadedTCPRequestHandler)
    ip, port = server.server_address
    server.serve_forever()

server_tcp_main("127.0.0.1", 10001)
