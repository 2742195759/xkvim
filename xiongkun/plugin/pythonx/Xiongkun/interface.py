import vim
from .func_register import *
from .vim_utils import *

@vim_register()
def set_yes(args):
    SetCurrentLine('yes')
