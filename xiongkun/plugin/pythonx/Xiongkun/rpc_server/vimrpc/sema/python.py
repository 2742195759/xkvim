from .sema_base import Sema, GetTextFromLocation
import re

class PySema(Sema):
    def __init__(self):
        pass
    def is_function_definition(self, loc, id_name=None):
        line = GetTextFromLocation(loc)
        if not line: return False
        if id_name is None: 
            return 'def' in line or 'class' in line
        else:
            return ('def ' + id_name) in line or 'class' + id_name in line


