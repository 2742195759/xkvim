"""  This file is plugin for remote terminal control:

     Terminal: open a new terminal in remote shell. [build environment]
     Sendfile: send file into remote shell.
"""

import vim
import sys
import os
import os.path as osp
from .func_register import *
from .vim_utils import *
from collections import OrderedDict

def send_keys(bufnr, keys):
    vim.eval(f"term_sendkeys({bufnr}, \"{keys}\")")

@vim_register(command="Bash", with_args=True)
def TerminalStart(args):
    pwd = GetPwd()
    path = os.path.join(pwd, "./.vim_clangd.py")
    if os.path.isfile(path): 
        config = absolute_import("vim_clangd", path)
        if hasattr(config, "wd"): 
            pwd = config.wd
    else: 
        print ("Not found .vim_clangd.py in your project directory.")
        return

    vim.command("tabe")
    vim.command("terminal")
    #vim.command("file ssh")
    vim.command("wincmd o")
    bufnr = vim.eval("bufnr()")
    send_keys(bufnr, f"ssh {config.ssh_url}\n")
    import time
    time.sleep(0.5)
    send_keys(bufnr, f"{config.ssh_passwd}\r\n")
    time.sleep(0.4)
    send_keys(bufnr, f"\r\n")
    time.sleep(0.4)
    send_keys(bufnr, f"{config.docker_cmd}\r\n")
    time.sleep(0.4)
    send_keys(bufnr, f"cd {pwd}\r\n")

@vim_register(command="BashHelp", with_args=True)
def TerminalHelper(args):
    print ("Keymap: ")
    print ("  <F1>  -> helper page")
    print ("  <M-a> -> start a abbreviate")
    print ("  <M-c> -> exit the terminal")
    print ("  <M-h> -> switch tabpage: previous")
    print ("  <M-l> -> switch tabpage: next")
    print ("  <M-n> -> normal mode")
    print ("  <M-p> -> page the \" register into the terminal")
    print ("  <M-f> -> start a command")
    print ("Abbreviate:")
    print ("  pp    -> PYTHONPATH=")
    print ("  proxy -> set proxy short cut")
    print ("  nopro -> set no proxy short cut")
    print ("  pdb   -> python pdb")

@vim_register(command="Write", with_args=True)
def TerminalWriteFile(args):
    if (len(args) < 1): 
        print ("Write python_obj -> write str(python_obj) into tmpfile, and open a new tabe to present it.")
    obj = args[0]
    def prediction(wnr):
        return vim.eval(f"getwinvar({wnr}, '&buftype')") == "terminal"
    bufnr = int(FindWindowInCurrentTabIf(prediction))
    tmpfile = "/tmp/tmp.txt"
    send_keys(bufnr, f"open('{tmpfile}', 'w').write(str({obj}))\n")
    with CurrentWindowGuard(): 
        vim.command("tabe")
        vim.command(f"read {tmpfile}")
