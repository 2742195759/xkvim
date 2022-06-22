from .vim_utils import *
import vim
from .func_register import *

@vim_register(keymap="<space>s")
def SwapWord():
    with NotChangeRegisterGuard("q"):
        pass
        

def test_NotChange():
    with NotChangeRegisterGuard("q"):
        vim.eval('setreg("q", "changed")')

"""
change the value of current word by register (@") 
"""
@vim_register(keymap="<space>w")
def ChangeWordByYank(args):
    vim.command('execute "normal cw\<C-R>0\<esc>"')
