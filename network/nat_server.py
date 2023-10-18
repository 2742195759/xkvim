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

def start_proxy_server(nat_ctl, listen_s, listen_c):
    print ("接受到了 nat client, 开始代理：")
    need_exit = False 
    pairs = []
    wait_for_pairing = {}
    while not need_exit:
        paired_sockets = [ i for i,j in pairs ]
        rs, ws, es = select.select([nat_ctl, listen_s, listen_c]+paired_sockets, [], [])
        for r in rs:
            if r == nat_ctl:
                need_exit=True # error happened. closed by paired sockets, exit.
            elif r == listen_c: 
                server, _ = r.accept() # may block
                pair_info = server.recv(28).decode("utf-8")
                assert pair_info.split(" ")[0].strip() == "connect"
                str_id = pair_info.split(" ")[1].strip()
                client = wait_for_pairing[str_id]
                del wait_for_pairing[str_id]
                pairs.append((client, server))
                pairs.append((server, client))
                print ("    创建结束...")
                
            elif r == listen_s:
                # send command to nat_client to start a new connect.
                print ("    接受到新请求：开始创建 nat client..")
                client, _ = r.accept() # may block
                print ("    Waiting for a new connect from nat client...")
                str_id = str(id(client))
                str_id_padding = " " * (20 - len(str_id)) + str_id
                os.write(nat_ctl.fileno(), b"connect " + str_id_padding.encode("utf-8") + b"\n")
                wait_for_pairing[str_id] = client
            else:
                pairs = find_pair_and_forward(pairs, r)

    for i,j in pairs:
        i.close()
    nat_ctl.close()
    print ("退出 nat client.")

def main():
    listen_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listen_s.bind(("0.0.0.0", args.port))
    listen_c.bind(("0.0.0.0", args.port+1)) # a socket listen in args.port+1 means wait for connect.
    listen_s.listen(5)
    while True:
        print ("开始等待 nat client 连接: ")
        nat_ctl_socket   , _ = listen_c.accept()
        start_proxy_server(nat_ctl_socket, listen_s, listen_c)

if __name__ == "__main__": 
    main()
