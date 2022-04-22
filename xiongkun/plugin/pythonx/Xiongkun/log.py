import os
from threading import Lock

mutex = Lock()
debug = 1
def log(*args):
    if debug == 0: return
    with mutex:
        out = " ".join([a.__str__() for a in args])
        with open("/home/data/vim_log.txe", "a") as fp :
            fp.writelines([out])
            fp.write("\n")

