import os
from threading import Lock
import vim
HOME_PREFIX=os.environ["HOME"]

mutex = Lock()
INFO  = 0
DEBUG = 1
NONE = 100
level = DEBUG 
def log(*args): # 0 
    #if level > 0: return 
    with mutex:
        out = " ".join([a.__str__() for a in args])
        with open(f"{HOME_PREFIX}/vim_log.txt", "a") as fp :
            fp.writelines([out])
            fp.write("\n")
            fp.flush()

def debug(*args): # 1
    if level > 1: return
    with mutex:
        out = " ".join([a.__str__() for a in args])
        with open(f"{HOME_PREFIX}/vim_log.txt", "a") as fp :
            fp.writelines([out])
            fp.write("\n")
            fp.flush()

def log_google(*args):
    with mutex:
        out = " ".join([a.__str__() for a in args])
        with open(f"{HOME_PREFIX}/google.txt", "a") as fp :
            fp.writelines([out])
            fp.write("\n")

from .func_register import vim_register
@vim_register(command="Log", with_args=False)
def OpenLog(args):
    vim.command(f"noswapfile tabe {HOME_PREFIX}/vim_log.txt")
    
