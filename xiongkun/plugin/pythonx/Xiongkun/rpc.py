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
import time

def create_rpc_handle(name, function_name, receive_name):
    vim.command(f"""
    function! {name}Server(channel, msg)
        let {receive_name}=a:msg
        py3 {function_name}.receive()
        redraw!
    endfunction
    """)

    vim.command(f"""function! {name}SendMessageSync(id, channel, package)
        call ch_sendraw(a:channel, a:package)
        while 1
            let out = ch_read(a:channel)
            if out == ""
                let status = ch_status(a:channel)
                if status == "fail" || status ==  "closed"
                    echom "[Warnings] Connection error: ".status
                endif
                continue
            endif
            let json = json_decode(out)
            call {name}Server(a:channel, out)
            if json[0] == a:id
                break
            endif
        endwhile
        return out
    endfunction""")
    
    vim.command(f""" 
    function! {name}ServerError(channel, msg)
        let {receive_name}=a:msg
        echom a:msg
    endfunction
    """)

    vim.command(f""" 
    function! {name}SendKeeplive(timer_id)
        py3 {function_name}.keeplive()
    endfunction
    """)

    vim.command("""
    call timer_start(30000, function('%sSendKeeplive'), {'repeat': -1})
    """ % name
    )


class RPCChannel:
    local_port = find_free_port()
    is_init = False
    rpc_log = f"/tmp/log.{local_port}"
    def __init__(self, name, remote_server, type, function):
        if remote_server is None: 
            port = RPCChannel.local_port
            remote_server = f"127.0.0.1:{port}"
            if not RPCChannel.is_init: 
                start_server_cmd = f"python3 {HOME_PREFIX}/xkvim/xiongkun/plugin/pythonx/Xiongkun/rpc_server/tcp_server.py --host 127.0.0.1 --port {port} 1>{RPCChannel.rpc_log} 2>&1"
                os.system(f"{start_server_cmd} &")
                RPCChannel.is_init = True


        self.channel_name = f"g:{name}_channel"
        self.receive_name = f"g:{name}_receive"
        self.name = name
        self.func_name = function
        create_rpc_handle(name, self.func_name, self.receive_name)
        config = {
            'mode': 'nl',
            'callback': f'{name}Server',
            'drop': 'auto',
            'noblock': 0,
            'waittime': 3000,
        }
        self.job_name = remote_server
        vimcommand(
            f'let {self.channel_name} = ch_open("{self.job_name}", {dict2str(config)})'
        )
        vimcommand(
            f'call ch_sendraw({self.channel_name}, "{type}\n")'
        )
        # package is like: [serve_id, server_name, [arg0, arg1, ...]]
        # respond is like: [serve_id, is_finished, return_val]
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
            return vim.eval(f'{self.name}SendMessageSync({sync}, {self.channel_name}, {str_package})')

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
    def __init__(self, name="RPC", remote_server=None, type="vimrpc", function="Xiongkun.rpc_server()"):
        self.channel = RPCChannel(name, remote_server, type, function)


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
        self.rpc = RPCServer(remote_server=self.host)
        print (self.root_directory, self.host)

    def effected_command(self):
        return "FF"

def get_address(): 
    host, port = remote_project.host.split(":")
    return host.strip(), port.strip()

remote_project = None

@vim_register(command="TestRPC")
def TestRPC(args):
    print (rpc_wait("filefinder.set_root", "/home/data"))

@vim_register(command="Show")
def ShowLog(args):
    vim.command(f"tabe {RPCChannel.rpc_log}")

def set_remote_project(config_file):
    global remote_project
    remote_project = RemoteProject(config_file)
