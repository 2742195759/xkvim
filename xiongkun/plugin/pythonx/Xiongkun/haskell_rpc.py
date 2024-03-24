import vim
from .vim_utils import *
from .rpc import RPCServer
from .func_register import *

class HaskellLocalServerCreator:
    def __init__(self):
        self._port = find_free_port()
        self._log_path = f"/tmp/log.{self._port}"

    def port(self): 
        return self._port

    def cmd (self): 
        return f"cd {HOME_PREFIX}/xkvim/haskell/vimrpc/ && HOST=127.0.0.1 PORT={self._port} ./main 1>{self._log_path} 2>&1"

    def log_path(self):
        return self._log_path

class HaskellPacker:
    def __init__(self):
        pass

    def pack(self, package):
        # package is like: [serve_id, server_name, [arg0, arg1, ...]]
        server_id, server_name, args = package
        d = {}
        d['method'] = server_name
        d['id'] = server_id
        d['param'] = args
        escaped = escape(json.dumps(package), '\\')
        escaped = escape(escaped, '"')
        str_package = '"' + escaped + '\n"'
        return str_package
        
    def unpack(self, strs):
        # respond is like: [serve_id, is_finished, return_val]
        d = json.loads(strs)
        print (d)
        return 0, 1, "error!"

@Singleton
class HaskellServer(RPCServer):
    def __init__(self):
        creator = HaskellLocalServerCreator()
        packer = HaskellPacker()
        print ("Create a haskell server.")
        super().__init__("HaskellRpc", None, "haskell_rpc", "Xiongkun.HaskellServer()", creator, packer)

@vim_register(command="TestHaskell")
def TestHaskell(args):
    def echo(x):
        print (x)
    HaskellServer().call("Concat", echo, "xxx", "yyy")
