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
import threading

@vim_register(keymap="i:<c-s>")
def InsertSurroundWith(args):
    line, col = vim_utils.GetCursorXY()
    left_sign = vim_utils.GetCurrentLine()[col-2] # -2 because offset = -1.
    right_sign = {'(': ')', '{': '}', '<': '>', '[': ']'}[left_sign]
    print ("Jumping to inclusive...")
    vim.command("BufferJump")
    new_line, new_col = vim_utils.GetCursorXY()
    vim.eval(f'feedkeys("\\<right>{right_sign}")')

@vim_register(keymap="gb")
def GotoBash(args):
    bufnr = vim.eval('bufnr("bash://remote")')
    vim.command(f"b {bufnr}")
