import shlex
import subprocess
import os
import json

debug = 0
def vlog(*arg, **args):
    if debug == 1: 
        print ("[DEBUG] ", *arg, **args)

class LSPPackage:# {{{
    def serialize(self, fp):
        data = self.getData()
        towrite = json.dumps(data)
        header = "Content-Length: %s\r\n\r\n" % str(len(towrite))
        vlog(header + towrite)
        fp.write(header + towrite)
        fp.flush()

    def deserialize(self, fp):
        while True:
            line = fp.readline()
            vlog(line)
            if "Content-Length: " in line:
                length = int(line.split("Content-Length: ")[1])
            if line.strip() == "":
                break
        response_raw = fp.read(length)
        self.setData(response_raw)

    def getData(self):
        """ get the data to send.
        """
        pass
    
    def setData(self, data):
        pass
# }}}

class LSPRequest(LSPPackage):# {{{
    rid = 0
    def __init__(self, method, param):
        self.id = LSPRequest.rid
        LSPRequest.rid += 1
        self.method = method
        self.param = param
        pass

    def getData(self):
        self.raw = {
            "jsonrpc": "2.0",
            "id" : str(self.id),
            "method": self.method,
            "params": self.param
        }
        return self.raw
    #}}}

class LSPResponse(LSPPackage):# {{{
    def setRequest(self, req):
        self.req = req

    def setData(self, data_string):
        self.data = json.loads(data_string)
        pass
# }}}
    
class Worker(): # {{{
    def __init__(self):
        self.initialize()
        pass

    def initialize(self):
        pass

    def getprocess(self): 
        pass

    def finish(self):
        pass

    def restart(self):
        self.finish()
        self.initialize()
        pass

    def _sendRequest(self, req):
        fp = self.getprocess().stdin
        req.serialize(fp)

    def _takeRespones(self):
        fp = self.getprocess().stdout
        rep = LSPResponse()
        rep.deserialize(fp)
        return rep

    def call(self, method, param):
        req = LSPRequest(method, param)
        self._sendRequest(req)
        rsp = self._takeRespones()
        rsp.setRequest(req)
        return rsp# }}}

class Indexer(Worker):# {{{
    def __init__(self, path):
        self.path = path
        super().__init__()
        pass 
    
    def initialize(self):
        """ NOTE: subprocess is shell==True, then the subprocess is the shell, and the .terminate() will terminate the shell but not the application.
            so the core will dumped by clangd-demo.

            set the shell=False, and the command is the shlex.split("SHELL_CMD"), we can avoid the dumped core.
        """
        self.proc = subprocess.Popen(shlex.split("/root/xkvim/cmd_script/clangd-index-finder --index_path=%s " % self.path), 
            shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True)

    def getprocess(self):
        return self.proc

    def finish(self):
        self.proc.terminate()
        self.proc.wait()
        self.proc = None
#}}}

def main():
    global debug
    debug = 1
    ID = Indexer("/home/data/llvm.dev")
    ID.call("fuzzy", {"Query": "fuzzy", "Scopes": [],"AnyScope": True})
    import pdb
    pdb.set_trace() 

if __name__ == "__main__":
    main()
