import os
from threading import Lock
import vim

mutex = Lock()
debug = 1
def log(*args):
    if debug == 0: return
    with mutex:
        out = " ".join([a.__str__() for a in args])
        with open("/home/data/vim_log.txt", "a") as fp :
            fp.writelines([out])
            fp.write("\n")

def log_google(*args):
    with mutex:
        out = " ".join([a.__str__() for a in args])
        with open("/home/data/google.txt", "a") as fp :
            fp.writelines([out])
            fp.write("\n")

from .func_register import vim_register
@vim_register(command="Log", with_args=False)
def OpenLog(args):
    vim.command("tabe /home/data/vim_log.txt")
    
