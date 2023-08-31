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
from collections import namedtuple
from nat_utils import forward_socket, connect_socket, find_pair, find_pair_and_forward

def parameter_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Support Args:")
    parser.add_argument("--port",  type=int,  help="data path")
    return parser.parse_args()

args = parameter_parser()

def start_proxy_server(nat_ctl, listener):
    print ("接受到了 nat client, 开始代理：")
    need_exit = False 
    pairs = []
    while not need_exit:
        paired_sockets = [ i for i,j in pairs ]
        rs, ws, es = select.select([nat_ctl, listener]+paired_sockets, [], [])
        for r in rs:
            if r == nat_ctl:
                need_exit=True # error happened. closed by paired sockets, exit.
            elif r == listener:
                # send command to nat_client to start a new connect.
                print ("    接受到新请求：开始创建 nat client..")
                os.write(nat_ctl.fileno(), b"connect")
                client, _ = listener.accept() # may block
                print ("    Waiting for a new connect from nat client...")
                server, _ = listener.accept() # may block
                pairs.append((client, server))
                pairs.append((server, client))
                print ("    创建结束...")
            else:
                pairs = find_pair_and_forward(pairs, r)

    for i,j in pairs:
        i.close()
    nat_ctl.close()
    print ("退出 nat client.")

def main():
    listen_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_s.bind(("0.0.0.0", args.port))
    listen_s.listen(5)
    while True:
        print ("开始等待 nat client 连接: ")
        nat_ctl_socket   , _ = listen_s.accept()
        start_proxy_server(nat_ctl_socket, listen_s)

if __name__ == "__main__": 
    main()
