# NATServer
# input_listen /  output_listenB
# forward input_listen -> output_listen


# NATWrapper
# input_connect / output_connect
# forward input_connect -> output_connect

import os
import sys
import select
import subprocess
import socket
import json
from nat_utils import forward_socket, connect_socket, find_pair, find_pair_and_forward
from collections import namedtuple

def parameter_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Support Args:")
    parser.add_argument("--input",                type=str, help="data path")
    parser.add_argument("--output",               type=str, help="data path")
    return parser.parse_args()

args = parameter_parser()

def string2address(s):
    t = s.split(":")
    return (t[0], int(t[1]))

def start_new_client_connect():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(string2address(args.output))
    return sock

def start_new_nat_connect():
    host, port = string2address(args.input)
    port += 1
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    return sock

def main():
    nat_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    nat_server.connect(string2address(args.input))
    pairs = []
    need_exit = False
    while not need_exit:
        paired_sockets = [ i for i,j in pairs ]
        rs, ws, es = select.select([nat_server]+paired_sockets, [], [])
        for r in rs:
            if r == nat_server:
                print ("    接受到新请求：开始发起链接...")
                bytes = os.read(r.fileno(), 28)
                assert bytes.decode("utf-8").split(" ")[0].strip() == "connect"
                new_conn = start_new_client_connect()
                new_nat = start_new_nat_connect()
                os.write(new_nat.fileno(), bytes)
                pairs.append((new_conn, new_nat))
                pairs.append((new_nat, new_conn))
            else:
                print ("接受到数据:")
                pairs = find_pair_and_forward(pairs, r)
    

if __name__ == "__main__": 
    main()

