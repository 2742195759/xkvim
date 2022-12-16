import vim
import traceback
from . import vim_utils
import time
from .func_register import vim_register
import threading
import subprocess
from functools import partial
import re

def get_history_isearch(word):
    cmd = f'ilist! /\<{word}\>/'
    return vim_utils.GetCommandOutput(cmd)

space = " *"
number = "[0-9]+"
allchar = ".*"

@vim_register(command="IJ", with_args=True)
def IJump(args):
    assert len(args) == 1, "a int is needed"
    id = int(args[0])
    word = vim_utils.GetCurrentWord()
    output = get_history_isearch(word)
    def is_item(line):
        return re.match(f"^{space}{number}", line) is not None

    def parse_fragment(line):
        mm = re.match(f"^{space}({number}):{space}({number})({allchar})$", line)
        return int(mm.group(1)), int(mm.group(2)), mm.group(3)
        
    filename = None
    lineno = None
    for line in output.split('\n'): 
        line = line.strip()
        if is_item(line):
            idx, lineno, text = parse_fragment(line)
            if idx == id: 
                break
        else: 
            filename = line
    loc = vim_utils.Location(filename, lineno, 0, 1)
    vim_utils.GoToLocation(loc, '.')
