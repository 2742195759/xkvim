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
import shlex
from .remote_fs import FileSystem

def ExecuteCommand(name, cmd, silent=True, block=True):
    log(f"Execute name={name} cmd={cmd} silent={silent} block={block}")
    if not block: 
        threading.Thread(target=ExecuteCommand, args=(name, cmd, silent, True), daemon=True).start()
        return 
    import json
    import requests
    headers = {"Content-Type":"application/json"}
    headers['Type'] = 'snd'
    headers['Name'] = name
    try:
        ret = requests.post("http://10.255.125.22:8084", data=json.dumps({"cmd": cmd, 'password':'807377414'}), headers=headers, timeout=3)
    except Exception as e:
        print(f"Failed to connect to server. {e}")
        return 
    if not silent or ret.status_code != 200:
        print (f"Return Code is {ret.status_code}, please check the server.")
        print (f"{ret.reason}")
    if not silent: 
        print (ret.text)

class OSMachine:
    def __init__(self, remote_name):
        self.name = remote_name

    def _join_cmd(self, cmd_list): 
        return " && ".join(cmd_list)

    def _command_escape(self, cmd):
        return cmd

    def execute(self, cmd, block=True):
        if isinstance(cmd, list):
            cmd = self._join_cmd(cmd)
        #cmd = self._command_escape(cmd)
        ExecuteCommand(self.name, cmd, True, block)
        
    def chrome(self, url):
        raise NotImplementedError()

    def send_file(self, filepath):
        raise NotImplementedError()

    def preview_file(self, filepath):
        raise NotImplementedError()

    def set_clipboard(self):
        raise NotImplementedError()

class MacMachine(OSMachine):
    def __init__(self, remote_name):
        super().__init__(remote_name)

    def _join_cmd(self, cmd_list): 
        return " && ".join(cmd_list)

    def chrome(self, url):
        cmd = """open "%s" """ % url
        self.execute(cmd)

    def send_file(self, filepath):
        from .converse_plugin import UploadFile
        UploadFile([filepath])
        cmd = [
            "unset https_proxy",
            "unset http_proxy",
            "curl http://10.255.125.22:8082/tmpfile.tar --output /tmp/tmpfile.tar ",
            "cd /tmp && tar -zxvf tmpfile.tar && rm -rf tmpfile.tar" , 
            "cd /tmp/tmpfile ",
        ]
        self.execute(cmd, block=True)

    def preview_file(self, filepath):
        if FileSystem().isfile(filepath):
            open_cmd = f"open /tmp/tmpfile/{os.path.basename(filepath)}"
        elif FileSystem().isdir(filepath): 
            open_cmd = f"open /tmp/tmpfile"
        else: 
            print("Please inputs a valid direcotry or file path.")
            return
        cmd = [ open_cmd ]
        self.execute(cmd)

    def set_clipboard(self):
        cmd = "curl http://10.255.125.22:8082/share.txt | pbcopy "
        self.execute(cmd)

class WindowMachine(OSMachine):
    def __init__(self, remote_name):
        super().__init__(remote_name)

    def chrome(self, url):
        cmd = f"start C:\PROGRA~1\Google\Chrome\Application\chrome.exe {url}"
        self.execute(cmd)

    def _command_escape(self, cmd: str):
        cmd = cmd.replace('&', '"&"')
        return cmd

    def send_file(self, filepath):
        from .converse_plugin import UploadFile
        UploadFile([filepath])
        cmd = [
            "curl http://10.255.125.22:8082/tmpfile.tar --output C:\\Users\\xiongkun\\Desktop\\linux\\XKConverser-develop\\tmpfile.tar",
            "cd C:\\Users\\xiongkun\\Desktop\\linux\\XKConverser-develop",
            "tar -zxvf tmpfile.tar && del tmpfile.tar " , 
        ]
        self.execute(cmd)

    def preview_file(self, filepath):
        if FileSystem().isfile(filepath):
            open_cmd = f"start tmpfile\\{os.path.basename(filepath)}"
        elif FileSystem().isdir(filepath): 
            open_cmd = f"start tmpfile"
        else: 
            print("Please inputs a valid direcotry or file path.")
            return
        cmd = [ 
            "cd C:\\Users\\xiongkun\\Desktop\\linux\\XKConverser-develop",
            open_cmd 
        ]
        self.execute(cmd)

    def set_clipboard(self):
        cmd = "curl http://10.255.125.22:8082/share.txt | clip "
        self.execute(cmd)

@vim_utils.Singleton
class RemoteConfig:
    def __init__(self):
        self.default_remote = vim_utils.GetConfigByKey("default_remote", f"{osp.join(vim_utils.HOME_PREFIX, 'xkvim')}")
        self.set_remote(self.default_remote)

    def get_machine(self):
        name2os = {
            'mac': MacMachine("mac"),
            'pc': WindowMachine("pc"),
        }
        return name2os[self.get_remote()]

    def set_remote(self, remote_name):
        self.remote_name = remote_name

    def get_remote(self):
        assert self.remote_name is not None, "Please set remote first."
        return self.remote_name

@contextmanager
def remote_machine_guard(remote):
    saved = RemoteConfig().get_remote()
    RemoteConfig().set_remote(remote)
    yield
    RemoteConfig().set_remote(saved)

