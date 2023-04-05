import vim
import traceback
from . import vim_utils
import time
from .func_register import vim_register
import threading
import subprocess
from functools import partial
import re
from .log import log

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

@vim_register(command="Getout", with_args=True)
def GetoutputFromCommand(args):
    assert len(args) >= 1, "Input the vim command from which you want get outputs."
    cmd = " ".join(args)
    output = vim_utils.GetCommandOutput(cmd)
    vim.command(f"vne")
    vim_utils.SetContent(output)
    vim_utils.memory_buffer()

vim.command("""
function! InteractDo()
    while 1
        let out = pyxeval("Xiongkun.DFAContext().run_step()")
        if out == "end"
            break
        elseif out == "redraw"
            redraw
        elseif out == "redraw!"
            redraw!
        elseif out == "nop"
            " do nothing
            let x = 1
        endif
    endwhile
    pyx Xiongkun.DFAContext().reset()
endfunction
""")

@vim_utils.Singleton
class DFAContext:
    def __init__(self):
        self.reset()
    
    def set_dfa(self, dfa):
        self._dfa = dfa

    def reset(self):
        def end():
            yield 'end'
        self.set_dfa(end())

    def pre_run(self):
        self._dfa = iter(self._dfa)
    
    def run_step(self):
        """ 
        Utililize `yield` and `yield from`.
        end | redraw | ???
        """
        try:
            return next(self._dfa)
        except StopIteration:
            return "end"
        except Exception as e: 
            print(f"Error happens: {e}")
            return "end"

def confirm(message):
    print(message)
    vim.eval("inputsave()")
    ch = int(vim.eval("getchar()"))
    vim.eval("inputrestore()")
    if chr(ch) == 'y': 
        return True
    else: 
        return False

def interactive_cdo(reg='q'): 
    qflist = vim.eval("getqflist()")
    for idx, item in enumerate(qflist):
        vim_utils.Location(vim.eval(f"bufname({item['bufnr']})"), 
                           int(item['lnum']), 
                           int(item['col']),).jump(".")
        yield "redraw"
        if confirm(f"[{idx+1}/{len(qflist)}] Preform @{reg} onto this line? (y/n)"): 
            try:
                vim.command(f"normal! @{reg}")
                vim.command(f"update")
            except:
                print("Error happens, skip this line.")

@vim_register(command="Replay", with_args=True, interactive=True)
def Replay(args):
    if len(args) == 0: 
        print("Replay <REG>")
        print("Example: Replay q -> 对所有的QuickfixList，将寄存器q中的内容作为命令执行")
        return 
    assert len(args) == 1
    reg = args[0]
    DFAContext().set_dfa(interactive_cdo(reg))

