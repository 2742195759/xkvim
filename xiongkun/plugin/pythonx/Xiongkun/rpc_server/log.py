import os
import sys
import json
import time
from threading import Lock, Thread

HOME_PREFIX=os.environ["HOME"]
mutex = Lock()
debug = 1

def log(*args):
    if debug == 0: return
    with mutex:
        out = " ".join([a.__str__() for a in args])
        with open(f"{HOME_PREFIX}/vim_log.txt", "a") as fp :
            fp.writelines([out])
            fp.write("\n")

