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

def LoadConfig(config_path="./.vim_clangd.py"): 
    pwd = GetPwd()
    path = os.path.join(pwd, config_path)
    if os.path.isfile(path): 
        config = absolute_import("vim_clangd", path)
        if hasattr(config, "wd"): 
            pwd = config.wd
    else: 
        raise RuntimeError(f"Not found {config_path} in your project directory.")
    setattr(config, "wd", pwd)
    return config

def TerminalStart(ssh_url, ssh_passwd, docker_cmd, work_dir=None, open_window=None):
    """ provide keys with: 
    """
    print (f"Connect to {ssh_url} , {docker_cmd}, {work_dir}")
    if not work_dir: 
        work_dir = GetPwd()
    if open_window is None: 
        vim.command("tabe")
        vim.command("terminal")
        vim.command("wincmd o")
    elif open_window == 'split':
        vim.command("vertical terminal")
    #vim.command("file ssh")
    bufnr = vim.eval("bufnr()")
    send_keys(bufnr, f"ssh {ssh_url}\n")
    import time
    time.sleep(1)
    send_keys(bufnr, f"{ssh_passwd}\r\n")
    time.sleep(0.4)
    send_keys(bufnr, f"\r\n")
    time.sleep(0.4)
    send_keys(bufnr, f"{docker_cmd}\r\n")
    time.sleep(0.4)
    send_keys(bufnr, f"cd {work_dir}\r\n")
    return bufnr

def load_config(args):
    if len(args) == 1: 
        config_file = "/home/data/.vim_clangd.py"
        from easydict import EasyDict as edict
        configs = LoadConfig(config_file)
        if (args[0] == 'ls'): 
            print("tf | torch | paddle | profile | wzf | cvpods")
            return
        else: 
            config = edict(getattr(configs, args[0]))
            config.wd = GetPwd()
    else: 
        config = LoadConfig()
    return config

@vim_register(command="Bash", with_args=True)
def BashStart(args=[]):
    config = load_config(args)
    TerminalStart(config.ssh_url, config.ssh_passwd, config.docker_cmd, config.wd)

@vim_register(command="VBash", with_args=True)
def VBashStart(args=[]):
    config = load_config(args)
    TerminalStart(config.ssh_url, config.ssh_passwd, config.docker_cmd, config.wd, 'split')

@vim_register(command="BashHelp", with_args=True)
def TerminalHelper(args):
    print ("Keymap: ")
    print ("  <F1>  -> helper page")
    print ("  <M-a> -> start a abbreviate")
    print ("  <M-q> -> exit the terminal")
    print ("  <M-h> -> switch tabpage: previous")
    print ("  <M-l> -> switch tabpage: next")
    print ("  <M-n> -> normal mode")
    print ("  <M-p> -> page the \" register into the terminal")
    print ("  <M-g> -> start a command")

@vim_register(command="PythonWrite")
def TerminalWriteFile(args):
    #print ("Write python_obj -> write str(python_obj) into tmpfile, and open a new tabe to present it.")
    obj = vim.eval('input("python object:")')
    def prediction(wnr):
        return vim.eval(f"getwinvar({wnr}, '&buftype')") == "terminal"
    bufnr = int(FindWindowInCurrentTabIf(prediction))
    tmpfile = "/home/data/tmp.txt"
    send_keys(bufnr, f"open('{tmpfile}', 'w').write(str({obj}))\n")
    with CurrentWindowGuard(): 
        vim.command("tabe")
        time.sleep(1.0)
        vim.command(f"read {tmpfile}")

terminal_abbreviate = [
    ["PY&THONPATH", 'PYTHONPATH=/home/data/Paddle/build/python'], 
    ["&breakpoint", "breakpoint()"], 
    ["&proxy", "export http_proxy=http://172.19.57.45:3128\nexport https_proxy=http://172.19.57.45:3128\n"], 
    ["&noproxy", "unset http_proxy\nunset https_proxy"], 
    ["&xk", "xiongkun"], 
    ["&CUDA_VISIBLE_DEVICES", "CUDA_VISIBLE_DEVICES=2"], 
    ["c&opy_file.sh", "/home/data/web/scripts/copy_file.sh"],
    ["&main_program", "paddle.static.default_main_program()"],
]

def get_abbreviate_list(bufnr, lists): 
    results = []
    for item in terminal_abbreviate:
        key, val = item
        new_item = [key, f'call term_sendkeys({bufnr}, "{val}")']
        results.append(new_item)
    results.append(["&write_python_obj", "PythonWrite"])
    return results

@vim_register(command="TerminalAbbre")
def TerminalAbbre(args):
    """
    abbreviate list for terminal windows.
    <M-a> to tigger this command.
    """
    def prediction(wnr):
        return vim.eval(f"getwinvar({wnr}, '&buftype')") == "terminal"
    bufnr = int(FindWindowInCurrentTabIf(prediction))
    PopupList(get_abbreviate_list(bufnr, terminal_abbreviate)).show()
