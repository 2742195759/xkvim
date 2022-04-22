from .cpp_sema import CppSema
from .py_sema import PySema
from .sema import Sema
import os.path as osp

def iscpp(filename):# {{{
    fff = ['.cpp', '.cc', '.h', '.hpp']
    for f in fff: 
        if f in osp.basename(filename): return True
    return False# }}}
def ispython(filename):# {{{
    return ".py" in osp.basename(filename)# }}}
class SemaPool: # {{{
    @staticmethod
    def get_sema(filename):
        if iscpp(filename): 
            return CppSema()
        if ispython(filename):
            return PySema()# }}}
        return Sema()
