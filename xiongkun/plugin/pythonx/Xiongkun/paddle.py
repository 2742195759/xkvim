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
from .remote_fs import Location

@vim_register(command="Build")
def SwitchBuildAndSource(args):
    """
    switch between build and non build directory in paddle.
    """
    path = vim_utils.CurrentEditFile(True)
    line, col = vim_utils.GetCursorXY()
    if 'build/' in path: 
        new_path = path.replace("build/", "")
    elif "Paddle/" in path:
        new_path = path.replace("Paddle/", "Paddle/build/")
    else: 
        print("Do Nothing.")
        new_path = path
    Location(new_path, line, col).jump()
