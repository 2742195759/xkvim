import os
import sys
import json
import time
from .decorator import *
from .functions import KillablePool
from .utils import GetSearchGrepArgs, GetSearchConfig, escape
import os.path as osp
import subprocess
from .sema.sema import SemaPool, LinePos

class GrepSearcher(AsyncServer):
    def __init__(self, queue, ppool):
        """ 
        Save a mapping from: name:String -> items:List(String)
        """
        self.ppool = ppool
        self.queue = queue

    def split_work(self, d):
        import glob 
        files = glob.glob(d + "/*")
        ex_dirs, ex_files = GetSearchConfig(d)
        def f(name):
            for ignore in ex_dirs + ex_files:
                ignore = ignore.replace("/", "")
                ignore = ignore.replace("*", "")
                if ignore == name: return False
            return True
        files = list(filter(f, files))
        files = [ f for f in files if osp.isdir(f) ]
        works = []
        for file in files: 
            abspath = osp.abspath(file)
            works.append(abspath)
        works.append("FILE:" + d)
        return works

    @stream_function 
    def search(self, id, directory, search_text): 
        extra_args = GetSearchGrepArgs(GetSearchConfig(directory))
        works = self.split_work(directory)
        num_worker=20
        with KillablePool(num_worker) as p:
            inputs = [(search_text, extra_args, work, id, self.queue) for work in works]
            outputs = p.map(do_grep_search, inputs)
        # reduce and post handle.
        gather = []
        for output in outputs: 
            res = output
            if len(res): gather.extend(res)
        return []

    @server_function
    def cancel_search(self): 
        self.ppool.terminal(self, "search") # close the last search process.

    def start_filter(self, items, search_text, func):
        num_worker=20
        with KillablePool(num_worker) as p:
            inputs = [(search_text, [item]) for item in items]
            outputs = p.map(func, inputs)
        gather = []
        for output in outputs: 
            res = output
            if len(res): gather.extend(res)
        return gather

    @async_function
    def sema_filter(self, items, search_text):
        return self.start_filter(items, search_text, filter_by_definition)

    @async_function
    def context_filter(self, items, search_text):
        return self.start_filter(items, search_text, filter_by_context)

def peek_line(filename, start, end):
    """
    read line from [start, end)
    """
    import linecache
    ret = []
    for i in range(start, end): 
        ret.append(linecache.getline(filename, i).strip())
    return ret

def filter_by_context(args):
    actual_text, items = args
    print (actual_text, items)
    result = []
    for item in items:
        context = "".join(peek_line(item['filename'], int(item['lnum'])-5, int(item['lnum'])+5))
        item['text'] = context
        if actual_text in context:
            result.append(item)
    return result

def filter_by_definition(args):
    search_text, items = args
    def definition_filter(item):
        l = LinePos(item['filename'], int(item['lnum'])-1)
        return SemaPool.get_sema(l.file).is_function_definition(l, search_text)
    items = list(filter(definition_filter, items))
    return items

def do_grep_search(args):
    search_text, extra_args, directory, id, queue = args
    if directory.startswith("FILE:"): 
        directory = directory.split("FILE:")[1].strip()
        sh_cmd = "find %s -maxdepth 1 -type f | LC_ALL=C xargs egrep -H -I -n %s \"%s\"" % (directory, " ".join(extra_args), escape(search_text))
    else: 
        sh_cmd = "LC_ALL=C egrep -I -H -n %s -r \"%s\" %s" % (" ".join(extra_args), escape(search_text), directory)
    child = subprocess.Popen(sh_cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
    results = []
    for idx, line in enumerate(child.stdout.readlines()):
        try:
            line = line.strip()
            filename = line.split(":")[0].strip()
            lnum = line.split(":")[1].strip()
            text = ":".join(line.split(":")[2:])
            result = {}
            result['filename'] = filename.strip()
            assert lnum.isnumeric(), "Not a valid number."
            result['lnum'] = lnum
            result['text'] = text.strip()
            result['cmd']  = "" + lnum
            result['source']  = "Grep"
        except Exception as e:
            continue
        results.append(result)
    queue.put((id, False, results))
    return results

def test_main():
    from server_cluster import ServerCluster, printer_process_fn
    import multiprocessing as mp
    mp_manager = mp.Manager()
    servers = ServerCluster(mp_manager)
    servers.start_queue(printer_process_fn)
    #servers.grepfinder = GrepSearcher(servers.queue)
    fn = servers.get_server_fn("grepfinder.search")
    fn (1, "/home/xiongkun/xkvim/", "do_grep_search")
    time.sleep(3)
    servers.stop()

if __name__ == "__main__":
    print ("start test grep search.py")
    test_main()


