from .indexer_finder import Indexer
from .vim_utils import *
from .func_register import *
from .windows import GlobalPreviewWindow
from os import path as osp
from .clangd_client import do_path_map
from . import remote_fs

"""
a example for result:
{
    'def': {'character': 5, 'line': 643},
    'name': 'Copy', 
    'scope': 'paddle::memory::',
    'signature': '',
    'type': 'function',
    'uri': 'file:///home/data/Paddle/paddle/fluid/memory/memcpy.cc'
}
"""

class SearchState: 
    def __init__(self):
        self.database = None
        self.last_results = None

state = SearchState()

def result_to_location(r):
    file = r['uri']
    if file.startswith("file://"): file = file[7:]
    file = do_path_map(file)
    if not osp.exists(file): return None
    return remote_fs.Location(file, r['def']['line'], r['def']['character'])

def filter_exactly(results, name, scope):
    results = [ r for r in results if r['name'] == name ]
    return results

def FindIndexer(args, filter=None, silent=False):
    """ input: [name]
    """
    name = full_name = args[0]
    scope = []
    with_scope = True
    if "::" in name: 
        name = full_name.split("::")[-1]
        scope = ["::".join(full_name.split("::")[:-1]) + "::"]
        with_scope = False
    if state.database is None: 
        if not silent: print("Please `ILoad <PATH-INDEXER>` first.")
        return None
    results = state.database.call("fuzzy", {"Query": name, "Scopes": scope, "AnyScope": with_scope}).data['result']
    if filter: 
        results = filter(results, name, scope)
    locs = []
    if results : 
        locs = [ result_to_location(r) for r in results ]
        locs = [ l for l in locs if l is not None]
    return locs

def PreviewResult(locs):
    if len(locs) == 0: 
        print("Not Found!")
    GlobalPreviewWindow.set_locs(locs)
    GlobalPreviewWindow.show()

@vim_register(command="ILoad", with_args=True)
def LoadIndexer(args):
    return 
    path = args[0]
    state.database = Indexer(path)

@vim_register(command="IFinish", with_args=False)
def FinishIndexer(args):
    state.database.finish()

@vim_register(command="IShow")
def ShowIndexer(args):
    if state.database: print ("Index path: ", state.database.path)
    else:  print ("No index loaded.")

@vim_register(command="IFuzzy", with_args=True)
def IFuzzy(args):
    results = FindIndexer(args, filter=None)
    PreviewResult(results)

@vim_register(command="IFind", with_args=True)
def IFind(args):
    #from .clangd_client import Clangd_GoTo, ClangdReparseCurFile
    #ClangdReparseCurFile([])
    #if Clangd_GoTo(['def'], preview=True): 
        #return 
    results = FindIndexer(args, filter=filter_exactly)
    if len(results): 
        IFuzzy(args)
    else:
        PreviewResult(results)
