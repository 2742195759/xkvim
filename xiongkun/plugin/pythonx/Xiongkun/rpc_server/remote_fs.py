import os
import sys
import json
import time
from decorator import *
from log import log
from functions import KillablePool


class RemoteFS:
    @server_function
    def fetch(self, path):
        with open(path, "r") as fp: 
            lines = fp.readlines()
        return "".join(lines)

    @server_function
    def store(self, path, content):
        try:
            with open(path, "w") as fp: 
                fp.write(content)
        except: 
            return "failed."
        return "success."

remotefs = RemoteFS()
