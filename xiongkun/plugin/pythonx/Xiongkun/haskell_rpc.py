import vim
from .vim_utils import *
from .rpc import RPCServer
from .func_register import *
from .log import debug
import json

class HaskellLocalServerCreator:
    def __init__(self):
        self._port = find_free_port()
        #self._port = 60537
        self._log_path = f"/tmp/log.{self._port}"

    def port(self): 
        return self._port

    def cmd (self): 
        return f"cd {HOME_PREFIX}/xkvim/haskell/vimrpc/ && HOST=127.0.0.1 PORT={self._port} ./main 1>{self._log_path} 2>&1"
        #return f"echo 'start...'"

    def log_path(self):
        return self._log_path

class HaskellPacker:
    def __init__(self):
        pass

    def pack(self, package):
        # package is like: [serve_id, server_name, [arg0, arg1, ...]]
        server_id, server_func, args = package
        d = {}
        d['method'] = server_func
        d['id'] = server_id
        d['param'] = args
        escaped = escape(json.dumps(d), '\\')
        escaped = escape(escaped, '"')
        str_package = '"' + escaped + '\n"'
        return str_package
        
    def unpack(self, strs):
        # respond is like: [serve_id, is_finished, return_val]
        d = json.loads(json.loads(strs))
        #debug("XKXKXK: ", d)
        return d['id'], True, d['res']

@Singleton
class HaskellServer(RPCServer):
    def __init__(self):
        creator = HaskellLocalServerCreator()
        packer = HaskellPacker()
        print ("Create a haskell server.")
        super().__init__("HaskellRpc", None, None, "Xiongkun.HaskellServer()", creator=creator, packer=packer)

haskell_server = HaskellServer()

@vim_register(command="TestHaskell")
def TestHaskell(args):
    #print(HaskellServer().call_sync("Concat", "xxx", "yyy"))
    print(HaskellServer().call_sync("sum", [12, 12, 12, 12, 12, 12]))

@vim_register(command="DrawGraph")
def DrawGraph(args):
    lines = GetVisualWords()
    lines = lines.replace("0x", "node_")
    graph = HaskellServer().call_sync("dotGraph", lines)
    file = tempfile()
    with open(file, "w") as fp :
        fp.write(graph)
    print (f"Write to {file}")
    print (f"use this to install dot command: sudo apt install graphviz")
    print (f"use this to get png:             dot {file} -Tpng -o /home/data/output.png")
