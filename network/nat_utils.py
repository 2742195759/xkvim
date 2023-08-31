import os
import sys
import select
import subprocess
import socket
import json

def pack_bytes(bytes): 
    pass

def unpack_bytes(bytes): 
    pass

def forward_socket(input_socket, output_socket):
    bytes = os.read(input_socket.fileno(), 10240)
    print (id(input_socket.fileno()), "=>", id(output_socket.fileno()))
    print ("[recv and send bytes]", bytes)
    if not bytes: # close
        return False
    os.write(output_socket.fileno(), bytes)
    return True

def connect_socket(input_socket, output_socket): # make two channel connected.
    print ("Start connecting two sockets...")
    need_exit = False 
    while not need_exit:
        rs, ws, es = select.select([input_socket, output_socket], [], [])
        for r in rs:
            if r == input_socket:
                need_exit = forward_socket(input_socket, output_socket)
            elif r == output_socket:
                need_exit = forward_socket(output_socket, input_socket)

    input_socket.close()
    output_socket.close()
    print("Exiting...")

def find_pair(cur, pairs):
    for i, j in pairs:
        if i == cur: 
            return j

def remove_from_pairs(a, pairs):
    results = []
    for i, j in pairs:
        if i == a or j == a: 
            continue
        results.append((i, j))
    return results

def find_pair_and_forward(pairs, current):
    target = find_pair(current, pairs)
    if forward_socket(current, target) == False:
        pairs = remove_from_pairs(current, pairs)
        pairs = remove_from_pairs(target, pairs)
        target.close()
        current.close()
    return pairs
    
