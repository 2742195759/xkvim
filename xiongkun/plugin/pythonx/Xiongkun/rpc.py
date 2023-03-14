from threading import Thread, Lock, currentThread
from queue import Queue
import traceback
import time
from contextlib import contextmanager
import ctypes
import inspect
from .log import log
import multiprocessing
import vim
from .vim_utils import *
import json
from .func_register import vim_register

class RPCServer:
    def __init__(self):
        config = {
            'in_mode': 'nl',
            'out_mode': 'nl',
            'out_io': "pipe",
            'in_io': "pipe",
            'out_cb': 'RPCServer',
            'callback': 'RPCServer',
            'err_cb': 'RPCServerError',
            #'exit_cb': 'RPCServer',
            'noblock': 1,
        }
        server_path = "python3 /root/xkvim/xiongkun/plugin/pythonx/Xiongkun/rpc_server/server.py"
        self.job_name = "g:rpc_job"
        self.channel_name = "g:rpc_channel"
        self.receive_name = "g:rpc_receive"
        self.id = 0
        vimcommand(
            f'let {self.job_name} = job_start("{server_path}", {dict2str(config)})'
        )
        vimcommand(
            f'let {self.channel_name} = job_getchannel({self.job_name})'
        )
        self.callbacks = {}
        self.increment_cache = {} # recode the newest request id: name -> newest_id
        self.increment_server = [
            'filefinder.search'
        ]

    def receive(self):
        msg = vimeval(f"{self.receive_name}")
        if not msg: 
            return
        self.on_receive(msg)

    def on_receive(self, msg):
        #log("[RPC]receive: ", msg)
        id, output = json.loads(msg)
        assert id in self.callbacks
        name, on_return = self.callbacks.pop(id)
        if name in self.increment_server and self.increment_cache[name] != id:
            return 
        on_return(output)

    def send(self, package):
        str_package = "\"" + escape(json.dumps(package), "\"") + "\n\""
        vim.eval(f'ch_sendraw({self.channel_name}, {str_package})')

    def call(self, name, on_return, *args):
        self.id += 1
        if name in self.increment_server:
            self.increment_cache[name] = self.id
        package = [self.id, name, args]
        self.callbacks[self.id] = (name, on_return)
        self.send(package)
    
rpc_server = RPCServer()

def rpc_call(name, on_return=None, *args): 
    """ rpc_call("goto", [1, 2], on_return)
        use the vim job machnism
        see `xiongkun/plugin/pythonx/Xiongkun/rpc_server/server.py` for remote function.
    """
    #return None
    do_nothing = lambda x: x
    if on_return is None: 
        on_return = do_nothing
    rpc_server.call(name, on_return, *args)

def rpc_wait(name, *args): 
    """ rpc_call("goto", [1, 2], on_return)
        use the vim job machnism
        see `xiongkun/plugin/pythonx/Xiongkun/rpc_server/server.py` for remote function.
    """
    output = None
    get = False
    def wait(out):
        nonlocal output
        nonlocal get
        output = out
        get = True
    rpc_server.call(name, wait, *args)
    #while True:
        #if get is True: return output
        #time.sleep(0.01)

@vim_register(command="RPCTest")
def TestRPC(args):
    def on_return(str):
        print(str)
    rpc_call("echo", on_return, "xiongkun")
    rpc_call("echo", on_return, "zhangsukun")

