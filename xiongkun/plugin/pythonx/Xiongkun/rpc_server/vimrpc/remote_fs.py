import os
import sys
import json
import time
from .decorator import *
from .functions import KillablePool
import os.path as osp

class RemoteFS:
    @server_function
    def fetch(self, path):
        if not osp.isfile(path):
            return f"Error: no such files: `{path}`"
        with open(path, "r") as fp: 
            lines = fp.readlines()
        return "".join(lines)

    @server_function
    def store(self, path, content):
        if not osp.isfile(path):
            return f"Error: no such files: `{path}`"
        try:
            with open(path, "w") as fp: 
                fp.write(content)
        except: 
            return "failed."
        return "success."
