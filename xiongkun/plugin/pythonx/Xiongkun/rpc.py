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
from .log import debug

class RPCServer:
    def __init__(self, remote_server=None):
        self.channel_name = "g:rpc_channel"
        self.receive_name = "g:rpc_receive"
        if remote_server is None: 
            config = {
                'in_mode': 'nl',
                'out_mode': 'nl',
                'out_cb': 'RPCServer',
                'callback': 'RPCServer',
                'err_cb': 'RPCServerError',
                'noblock': 1,
                'out_io': "pipe",
                'in_io': "pipe",
            }
            server_path = f"python3 {HOME_PREFIX}/xkvim/xiongkun/plugin/pythonx/Xiongkun/rpc_server/server.py"

            self.job_name = "g:rpc_job"
            vimcommand(
                f'let {self.job_name} = job_start("{server_path}", {dict2str(config)})'
            )
            vimcommand(
                f'let {self.channel_name} = job_getchannel({self.job_name})'
            )
        else: 
            config = {
                'mode': 'nl',
                'callback': 'RPCServer',
                'drop': 'auto',
                'noblock': 1,
            }
            self.job_name = remote_server
            vimcommand(
                f'let {self.channel_name} = ch_open("{self.job_name}", {dict2str(config)})'
            )
        self.id = 0
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
        #debug("[RPC]receive: ", msg)
        id, output = json.loads(msg)
        if id not in self.callbacks: 
            return
        name, on_return = self.callbacks.pop(id)
        if name in self.increment_server and self.increment_cache[name] != id:
            return 
        on_return(output)

    def send(self, package, sync=None):
        escaped = escape(json.dumps(package), '\\')
        escaped = escape(escaped, '"')
        str_package = '"' + escaped + '\n"'
        from .log import log
        if sync is None: 
            vim.eval(f'ch_sendraw({self.channel_name}, {str_package})')
        else: 
            assert isinstance(sync, int)
            return vim.eval(f'SendMessageSync({sync}, {self.channel_name}, {str_package})')

    def call_common(self, name, on_return, *args):
        self.id += 1
        if name in self.increment_server:
            self.increment_cache[name] = self.id
        package = [self.id, name, args]
        self.callbacks[self.id] = (name, on_return)
        return self.id, package

    def call(self, name, on_return, *args):
        id, package = self.call_common(name, on_return, *args)
        self.send(package)

    def call_sync(self, name, *args):
        id, package = self.call_common(name, lambda x: x, *args)
        return self.send(package, id)

local_rpc = None

def rpc_server():
    global local_rpc
    if remote_project is None: 
        if local_rpc is None: 
            local_rpc = RPCServer()
        return local_rpc
    return remote_project.rpc

def get_directory():
    from .remote_fs import to_remote
    if remote_project is None: 
        return vim.eval("getcwd()")
    else: 
        return to_remote(remote_project.root_directory)

def rpc_call(name, on_return=None, *args): 
    """ rpc_call("goto", [1, 2], on_return)
        use the vim job machnism
        see `xiongkun/plugin/pythonx/Xiongkun/rpc_server/server.py` for remote function.
    """
    #return None
    assert on_return is None or callable(on_return), "on_return must be a callable function"
    do_nothing = lambda x: x
    if on_return is None: 
        on_return = do_nothing
    rpc_server().call(name, on_return, *args)


def rpc_wait(name, *args): 
    """ rpc_call("goto", [1, 2], on_return)
        use the vim job machnism
        see `xiongkun/plugin/pythonx/Xiongkun/rpc_server/server.py` for remote function.
    """
    msg = rpc_server().call_sync(name, *args)
    id, output = json.loads(msg)
    return output

class RemoteProject: 
    def __init__(self, config_file):
        import yaml  
        if not os.path.exists(config_file): 
            print ("not exist.")
            return
        with open(config_file, 'r') as f:  
            data = yaml.safe_load(f)  
        self.root_directory = data['root']
        self.host = data['host']
        self.rpc = RPCServer(self.host)
        print (self.root_directory, self.host)

    def effected_command(self):
        return "FF"

remote_project = None

@vim_register(command="SetRPCProject", with_args=True, command_completer="file")
def SetRPCServer(args):
    global remote_project
    remote_project = RemoteProject(args[0])

@vim_register(command="TestRPC")
def TestRPC(args):
    print (rpc_wait("filefinder.set_root", "/home/data"))
