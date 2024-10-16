from .sema import Sema
from .vim_utils import GetTextFromLocation
import re
from .log import log

class PySema(Sema):
    def __init__(self):
        pass
    def is_function_definition(self, loc, id_name=None):
        line = GetTextFromLocation(loc.to_base(0))
        log("pysema: ", line, id_name)
        if id_name is None: 
            return 'def' in line or 'class' in line
        else:
            return ('def ' + id_name) in line or 'class' + id_name in line

