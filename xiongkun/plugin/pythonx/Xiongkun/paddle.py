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
from .remote_fs import FileSystem, check_buffer_newest

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

@vim_register(command="SyncBuild")
def SyncFilesBetweenBuild(args):
    """
    Sync between build and non build directory in paddle.
    """
    if not check_buffer_newest(): 
        return
    path = vim_utils.CurrentEditFile(True)
    line, col = vim_utils.GetCursorXY()
    if 'build/' in path: 
        new_path = path.replace("build/", "")
    elif "Paddle/" in path:
        new_path = path.replace("Paddle/", "Paddle/build/")
    else: 
        print("Do Nothing.")
        new_path = path
    if FileSystem().command(f"cp {path} {new_path}"): 
        print (f"Successful sync {path} -> {new_path}")

@vim_register(command="AutoSyncBuild")
def StartAutoSyncBuild(args):
    """
    Sync between build and non build directory in paddle.
    """
    commands(""" 
augroup PaddleAutoSyncBuild
    autocmd!
    autocmd BufWriteCmd *.py SyncBuild
augroup END
    """)

