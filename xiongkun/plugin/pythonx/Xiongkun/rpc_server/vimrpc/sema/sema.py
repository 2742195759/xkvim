from .cpp import CppSema
from .python import PySema
from .sema_base import Sema, GetTextFromLocation
import os.path as osp

class VimSema:
    def is_function_definition(self, loc, id_name=None):
        line = GetTextFromLocation(loc)
        if not line: return False
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

class LinePos:
    def __init__(self, file, line):
        # line is 0-based
        self.file = file
        self.line = line

