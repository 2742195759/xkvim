from .vim_utils import *
from .func_register import *
from contextlib import contextmanager 

@contextmanager
def NotChangeRegisterGuard(regs):
    saved = []
    for reg in regs:
        saved.append(vim.eval('getreginfo("%s")'%escape(reg)))
    yield
    v = VimVariable()
    for save, reg in zip(saved, regs):
        v.assign(save)
        vim.eval('setreg("%s", %s)'%(escape(reg), v))
    v.delete()

@vim_register(keymap="<space>s")
def SwapWord():
    with NotChangeRegisterGuard("q"):
        pass
        

def test_NotChange():
    with NotChangeRegisterGuard("q"):
        vim.eval('setreg("q", "changed")')
