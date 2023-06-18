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

class RPCChannel:
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
                'noblock': 0,
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
                'noblock': 0,
                'waittime': 3000,
            }
            self.job_name = remote_server
            print (remote_server)
            vimcommand(
                f'let {self.channel_name} = ch_open("{self.job_name}", {dict2str(config)})'
            )
            vimcommand(
                f'call ch_sendraw({self.channel_name}, "vimrpc\n")'
            )
        # package is like: [serve_id, server_name, [arg0, arg1, ...]]
        # respond is like: [serve_id, is_finished, [return_val]]
        self.id = 0
        self.receives = {}
        self.callbacks = {} # id -> (on_receive)

    def receive(self):
        msg = vimeval(f"{self.receive_name}")
        if not msg: return
        self.on_receive(msg)

    def on_receive(self, msg):
        id, is_finished, output = json.loads(msg)
        if id not in self.callbacks: 
            # maybe keeplive package.
            return
        on_return = self.callbacks[id]
        on_return(id, is_finished, output)
        if is_finished: 
            if id in self.callbacks: 
                self.callbacks.pop(id)

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

    def stream_new(self):
        class RPCStream:
            def __init__(self, channel, id):
                self.id = id
                self.is_deleted=False
                self.channel = channel
            
            def send(self, name, sync=None, *args):
                assert self.is_deleted == False
                package = [self.id, name, args]
                return self.channel.send(package, sync)

            def delete(self):
                self.is_deleted = True
                self.channel.stream_del(self)

            def register_hook(self, on_receive): 
                self.channel.callbacks[self.id] = on_receive
                
        self.id += 1
        return RPCStream(self, self.id)

    def stream_del(self, stream): 
        if stream.id in self.callbacks: 
            self.callbacks.pop(stream.id)

def dummy_callback(*args, **kwargs):
    return None

class RPCServer:
    def __init__(self, remote_server=None):
        self.channel = RPCChannel(remote_server)


    def call(self, name, on_return, *args):
        stream = self.channel.stream_new()
        def on_return_wrapper(id, is_finished, output): 
            #if not is_finished: cached_inputs.append(output)
            assert is_finished == True, "received is_finished == False, please use stream rpc."
            on_return(output)
            stream.delete()
        stream.register_hook(on_return_wrapper)
        stream.send(name, None, *args)
        return stream


    def call_sync(self, name, *args):
        stream = self.channel.stream_new()
        stream.register_hook(dummy_callback)
        output = stream.send(name, stream.id, *args)
        id, is_finished, output = json.loads(output)
        return output


    def call_stream(self, name, on_return, on_finish, *args): 
        """
        call a function, and get output as a stream.
        with is_finished set, we delete.
        """
        stream = self.channel.stream_new()
        def on_return_wrapper(id, is_finished, output): 
            #if not is_finished: cached_inputs.append(output)
            if is_finished: 
                on_finish(output)
                stream.delete()
            else: 
                on_return(output)
        stream.register_hook(on_return_wrapper)
        stream.send(name, None, *args)
        return stream


    def receive(self): # for hooker.
        self.channel.receive()

    def keeplive(self):
        self.channel.send([-1, "keeplive", []])

        

local_rpc = None

def rpc_server():
    global local_rpc
    if remote_project is None: 
        if local_rpc is None: 
            local_rpc = RPCServer()
        return local_rpc
    return remote_project.rpc


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
    return rpc_server().call_sync(name, *args)

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

def get_address(): 
    host, port = remote_project.host.split(":")
    return host.strip(), port.strip()

remote_project = None

vim.command(
""" 
function! SendKeeplive(timer_id)
    py3 Xiongkun.rpc_server().keeplive()
endfunction
""")

vim.command(
"""
call timer_start(10000, function('SendKeeplive'), {'repeat': -1})
"""
)

@vim_register(command="SetRPCProject", with_args=True, command_completer="file")
def SetRPCServer(args):
    global remote_project
    remote_project = RemoteProject(args[0])
    vim.command("wincmd o")

@vim_register(command="TestRPC")
def TestRPC(args):
    print (rpc_wait("filefinder.set_root", "/home/data"))
