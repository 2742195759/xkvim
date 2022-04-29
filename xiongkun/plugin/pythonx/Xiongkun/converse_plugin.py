import vim
import subprocess
import os
from os import path as osp
from . import vim_utils
from .func_register import *
import random
import threading
import json
from contextlib import contextmanager
import time
import os.path as osp
from .log import log, log_google
from urllib.parse import quote

def ExecuteCommand(name, cmd, silent=True):
    import json
    import requests
    headers = {"Content-Type":"application/json"}
    headers['Type'] = 'snd'
    headers['Name'] = name
    ret = requests.post("http://10.255.125.22:8084", data=json.dumps({"cmd": cmd, 'password':'807377414'}), headers=headers)
    if not silent: 
        print (ret.status_code, ret.reason)
        print (ret.text)

@vim_register(command="Google", with_args=True)
def Google(args):
    from os import path as ops
    text = " ".join(args)
    if not text: 
        text = vim_utils.GetCurrentWord()
    if text: log_google(text)
    url_text = quote(text)
    """ 
    MacOs: open "http://" can open a http website in default browser.
    """
    cmd = """open "https://www.google.com.hk/search?q=%s" """ % url_text
    log(cmd)
    ExecuteCommand("mac", cmd, silent=True)
