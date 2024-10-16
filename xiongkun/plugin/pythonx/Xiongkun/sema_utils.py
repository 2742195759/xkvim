from .cpp_sema import CppSema
from .py_sema import PySema
from .vim_utils import GetTextFromLocation
from .sema import Sema
import os.path as osp

class VimSema:
    def is_function_definition(self, loc, id_name=None):
        line = GetTextFromLocation(loc)
        return 'function' in line

def iscpp(filename):# {{{
    fff = ['.cpp', '.cc', '.h', '.hpp']
    for f in fff: 
        if f in osp.basename(filename): return True
    return False# }}}
def ispython(filename):# {{{
    return ".py" in osp.basename(filename)# }}}
def isvim(filename):# {{{
    return ".vim" in osp.basename(filename)# }}}
class SemaPool: # {{{
    @staticmethod
    def get_sema(filename):
        if iscpp(filename): 
            return CppSema()
        if ispython(filename):
            return PySema()# }}}
        if isvim(filename):
            return VimSema()
        return Sema()
