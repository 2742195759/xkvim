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
from .remote_fs import FileSystem
from .rpc import get_address
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
    if not FileSystem().is_remote(): 
        print ("Bash only support remote mode! :terminal is suit for local mode.")
        return
    host, port = get_address()
    print (get_address())
    configs = '{"term_name": "remote://bash"}'
    vimeval(f'term_start("python3 {HOME_PREFIX}/xkvim/xiongkun/plugin/pythonx/Xiongkun/rpc_server/client/bash_client.py --host {host} --port {port}", {configs})')
    time.sleep(1)
    bufnr = vim.eval("bufnr()")
    send_keys(bufnr, f"cd {FileSystem().cwd}\n")
    send_keys(bufnr, f"resize\n")

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

def get_abbreviate_list(bufnr): 
    from .remote_fs import FileSystem
    from .rpc import rpc_wait
    project_abbreviate = rpc_wait("config.get_config_by_key", "terminal_abbrev", FileSystem().getcwd())
    global_abbreviate = GetConfigByKey("terminal_abbreviate", directory=os.path.join(getHomeDirectory(), "xkvim"))
    terminal_abbreviate = global_abbreviate + project_abbreviate
    results = []
    for item in terminal_abbreviate :
        key, val = item
        if val.startswith(':'): 
            new_item = [key, f"{val[1:]}"]
        else:
            new_item = [key, f'call term_sendkeys({bufnr}, "{val}")']
        results.append(new_item)
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
    abbres = get_abbreviate_list(bufnr)
    from .buf_app import CommandList
    CommandList("terminal_abbreviates", [n[0] for n in abbres], [n[1] for n in abbres]).start()
