from .vim_utils import *
import vim
from .func_register import *
from contextlib import contextmanager 

def SmartFunctionCall():
    return "sdf"

#@vim_register(keymap="i:(")
#def _SmartFunctionCall(args):
    #return SmartFunctionCall()
