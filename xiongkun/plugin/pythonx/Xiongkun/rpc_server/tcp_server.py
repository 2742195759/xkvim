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
# This requires Python 3.8 or later.

from __future__ import print_function
import json
import socket
import sys
import threading
from threading import Thread
from server_cluster import ServerCluster, YiyanServerCluster
from vimrpc.decorator import InQueue
from servers.bash_server import bash_server
from servers.bash_server_pool import reconnect_bash, NamedBashPool
from servers.lsp_server import lsp_server
import select
from socket_stream import SockStream
from log import log
import platform
import multiprocessing as mp
import signal
import os

try:
    # Python 3
    import socketserver
except ImportError:
    # Python 2
    import SocketServer as socketserver

def bash_manager(socket, bash_pool):
    # 3 command to execute: 
    # connect name
    # delete name
    # list
    command = safe_read_line(socket)
    if command is None:
        return
    print ("Bash Command: ", command)
    if command.startswith(b"list"):
        names = bash_pool.names()
        socket.sendall(b"\n".join(names))
        print (b"\n".join(names))
        return
    elif command.startswith(b"connect"):
        if len(command.split(b" ")) == 1:
            # connect a new bash.
            print ("create session local bash...")
            proc = mp.Process(target=bash_server, args=(socket, ))
            return proc
        else: 
            name = command.split(b" ")[1]
            print ("[BashPool] reconnect bash... : ", name)
            bash_proc, master_fd = bash_pool.get_bash_worker(name)
            print (f"[BashPool] slave_process state is {bash_proc.poll()}")
            proc = mp.Process(target=reconnect_bash, args=(socket, master_fd))
            return proc
    elif command.startswith(b"delete"):
        if len(command.split(b" ")) == 1: 
            print ("Not found name to delete.")
            return
        name = command.split(b" ")[1]
        bash_pool.delete(name)

def vim_rpc_loop(sock, services_cluster_cls, queue):
    print ("===== start a vim rpc server ======")
    rfile = sock.makefile('rb', 10240)
    wfile = sock.makefile('wb', 10240)
    def send(obj):
        encoded = json.dumps(obj) + "\n"
        wfile.write(encoded.encode('utf-8'))
        wfile.flush()

    servers = services_cluster_cls(queue)
    servers.start_queue(send)
    stream = SockStream()

    while True:
        rs, ws, es = select.select([rfile.fileno()], [], [], 3.0)
        sys.stdout.flush()
        sys.stderr.flush()
        if rfile.fileno() in rs:
            try:
                bytes = sock.recv(10240)
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
    sock.close()
    print ("===== stop a vim rpc server ======")

class ThreadedTCPServer(socketserver.TCPServer):
    pass

def read_single_char(socket, timeout=1):
    ready = select.select([socket], [], [], timeout)
    if ready[0]:
        data = socket.recv(1)
        if data == b'':
            # closed by other side.
            raise ConnectionResetError("connection is closed by other side.")
        return data
    else: 
        # timeout 
        raise TimeoutError("read single char timeout for ", timeout, " seconds.")

def read_line(socket, timeout=1):
    received = b""
    c = read_single_char(socket, timeout)
    while c != b'\n': # read just one line and don't buffer.
        received += c
        c = read_single_char(socket, timeout)
    return received

def server_wrapper(listen_s, func, *args, **kwargs):
    listen_s.close()
    func(*args, **kwargs)

def safe_read_line(socket):
    try:
        data = read_line(socket, 5)
        return data
    except TimeoutError:
        print ("[TCPServer] Timeout when receiving... exiting.")
        return None
    except ConnectionResetError:
        print ("[TCPServer] Connection is reset by other side.")
        return None
    except Exception as e:
        print ("[TCPServer] Receive exception: ", e, "\njust ignored.")
        return None
    

def connection_handle(listen_s, socket, mp_manager, bash_pool):
    # override the main process signal handler.
    print("=== socket opened ===")
    mode = safe_read_line(socket)
    if mode is None:
        return
    print ("[TCPServer] receive: ", mode)
    mode = mode.strip()
    proc = None
    if mode == b"bash": 
        proc = bash_manager(socket, bash_pool)
    elif mode == b"vimrpc":
        proc = mp.Process(target=server_wrapper, args=(listen_s, vim_rpc_loop, socket, ServerCluster, mp_manager))
    elif mode == b"yiyan":
        proc = mp.Process(target=server_wrapper, args=(listen_s, vim_rpc_loop, socket, YiyanServerCluster, mp_manager))
    elif mode == b"lsp":
        proc = mp.Process(target=server_wrapper, args=(listen_s, lsp_server, socket, mp_manager))
    else: 
        print (f"Unknow command. {mode}")
    sys.stdout.flush()
    if proc: 
        proc.daemon=False
        proc.start()
    return proc

def server_tcp_main(HOST, PORT):
    mp_manager = mp.Manager()
    bash_pool = NamedBashPool()
    child_pid = []
    listen_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_s.bind((HOST, PORT))
    listen_s.listen(20)
    print ("开始监听: ", (HOST, PORT))
    try:
        while True: 
            r, w, e = select.select([listen_s], [], [], 10.0)
            if listen_s in r:
                try:
                    cnn, addr = listen_s.accept()
                    worker = connection_handle(listen_s, cnn, mp_manager, bash_pool)
                    cnn.close() # close in this process.
                    if worker is not None: 
                        child_pid.append(worker)
                except ConnectionResetError:
                    break
                finally:
                    cnn.close() # close in this process.
            for proc in child_pid:
                proc.join(0.1)
            child_pid = [ proc for proc in child_pid if proc.exitcode is None ] # None means not exit.
            print (f"End Joining Child Processes... [{len(child_pid)}]")
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
    args = parameter_parser()
    server_tcp_main(args.host, int(args.port))
