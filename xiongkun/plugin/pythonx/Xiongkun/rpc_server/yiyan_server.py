import os
import sys
import json
import time
from decorator import *
from log import log
from functions import KillablePool

class Yiyan:
    def __init__(self):
        self.cmd = f"bash {os.environ['HOME']}/xkvim/bash_scripts/yiyan.sh"
        self.child = None
        pass

    @server_function
    def init_yiyan(self): 
        import subprocess
        # create subprocess
        if self.child is not None: 
            self.child.stdin.close()
        try:
            child = subprocess.Popen(self.cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
            self.child = child
            return "success"
        except:
            return "failed"

    def check_alive(self):
        if self.child is None: return False
        if self.child.poll() is None: return True
        return False

    @server_function
    def query(self, query): 
        if self.check_alive() is False: 
            self.init_yiyan(0)
        query = query.strip("\n\r")
        self.child.stdin.write(query + "\n")
        self.child.stdin.flush()
        lines = []
        while True:
            line = self.child.stdout.readline()
            if line.strip() == "": break
            lines.append(line)
        return lines

def test_main():
    yiyan = Yiyan()
    yiyan.init_yiyan(0)
    print(yiyan.query(1, "hello?"))
    print(yiyan.query(2, "你好，你是谁?"))
    breakpoint() 

if __name__ == "__main__":
    test_main()
