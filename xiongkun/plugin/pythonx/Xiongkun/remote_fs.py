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
import os.path as osp
from .rpc import rpc_call, rpc_wait, rpc_server
from .vim_utils import vimcommand, IsBufferExist
import os
import codecs

def is_buf_remote():
    remote = vim.eval("getbufvar(bufnr(), 'remote')")
    return remote == "remote"

def update_buffer_timestamp(filepath):
    # set timestamp
    timestamp = str(FileSystem().timestamp(filepath))
    assert timestamp != "-1"
    bufnr = vim.eval(f"bufnr('{filepath}')")
    vim.eval(f"setbufvar({bufnr}, 'timestamp', '{timestamp}')")

def check_buffer_newest():
    bufname = vim.eval("bufname()")
    if FileSystem().is_buffer_lastest(bufname) is False:
        vim.command("echow 'buffer is not the latest version, RE to update.'")
        return False
    return True

@vim_register(command="RemoteSave")
def RemoteSave(args):
    if is_buf_remote():
        bufname = vim.eval("bufname()")
        if not check_buffer_newest(): 
            return
        filepath = FileSystem().filepath(bufname)
        bufnr = vim.eval(f"bufnr('{bufname}')")
        lines = vim.eval(f"getbufline({bufnr}, 1, '$')")
        if FileSystem().store(filepath, "\n".join(lines)) is not True: 
            vim.command(f"echom '{FileSystem().last_error()}'")
        update_buffer_timestamp(filepath)
        vim.command("set nomodified")
    else:
        vim.command("noautocmd write")
        vim.command("set nomodified")
        
@vim_register(command="RE", with_args=True, command_completer="customlist,RemoteFileCommandComplete")
def RemoteEdit(args):
    """ 
    Remote Edit command: RE
    RE <abspath>
    >>> RE + <
    """
    if len(args) == 0: 
        bufname = vim.eval("bufname()")
        filepath = FileSystem().filepath(bufname)
        FileSystem().edit(filepath, force=True)
        return
    if not FileSystem().exists(args[0]): 
        FileSystem().create_node(args[0])
    FileSystem().edit(args[0])
            
def start_register_remote_write(bufnr):
    bufnr = int(bufnr)
    vim_utils.commands(f""" 
    autocmd BufWriteCmd <buffer={bufnr}> RemoteSave
    autocmd FileChangedRO <buffer={bufnr}> set noreadonly
    """)

def GoToBuffer(bufnr, method):
    """
    jump to a location.
    supported method: 
    1. 's': split
    2. 'v': vertical
    3. 't': tabe
    4. '.' | 'e': current window
    5. 'p': preview open
    6. 'b': buffer open
    6. 'sb': buffer open
    """
    norm_methods = {
        'e': f'enew\nsetlocal bufhidden=wipe\nkeepjumps b {bufnr}',
        '.': f'enew\nsetlocal bufhidden=wipe\nkeepjumps b {bufnr}',
        't': 'tabe!\nsetlocal bufhidden=wipe\nkeepjumps b {bufnr}'.format(bufnr=bufnr),
        'v': 'vne!\nsetlocal bufhidden=wipe\nkeepjumps b {bufnr}'.format(bufnr=bufnr),
        's': f'keepjumps sb {bufnr}',
        'b': f'keepjumps b {bufnr}',
        'sb': f'keepjumps vertical sb {bufnr}',
    }
    commands = norm_methods[method]
    vim_utils.commands(commands)
    

def GoToLocation(location, method):
    #view_methods = {
        #'e': 'noswapfile e',
        #'.': 'noswapfile e',
        #'p': 'noswapfile pedit',
        #'s': 'noswapfile split',
        #'t': 'noswapfile tabe',
        #'v': 'noswapfile vne',
        #'b': 'noswapfile b',
        #'sb':'noswapfile vertical sb',
    #}
    bufnr = FileSystem().bufload_file(location.getfile())
    GoToBuffer(bufnr, method)
    vimcommand(f":{location.getline()}")
    if location.getcol() != 1:
        vimcommand("normal %d|"%(location.getcol()))
    vimcommand("normal zv")

class Location: 
    def __init__(self, file, line=1, col=1, base=1):
        if isinstance(file, int): 
            file = vim.eval(f"bufname({file})")
        self.full_path = FileSystem().abspath(file)
        self.line = line
        self.col = col
        self.base = base

    def getline(self):  
        return self.line 
    
    def getcol(self):   
        return self.col

    def getfile(self):
        return self.full_path

    def to_base(self, new_base):
        col = self.col + new_base - self.base
        row = self.line + new_base - self.base
        return Location(self.full_path, row, col, new_base)

    def jump(self, cmd="."):
        GoToLocation(self, cmd)


def HasSwapFile(path):
    abspath = os.path.abspath(path)
    basename = os.path.basename(abspath)
    pattern = os.path.dirname(abspath) + "/." + basename + ".*"
    import glob
    if len(glob.glob(pattern)): 
        return True
    return False


@vim_register(command="GotoFile", keymap="gf")
def GotoFile(args):
    filepath = vim.eval('expand("<cfile>")')
    FileSystem().edit(filepath)

class DirectoryTree:
    def __init__(self, type, fullpath, extra_data=None):
        self.child = []
        self.father = None
        self.type = type
        self.fullpath = fullpath
        self.is_open = False
        self.extra_data = extra_data

    def visit_bfs(self):
        for file in self.files(): 
            yield file
        for d in self.dirs():
            yield from d.visit_bfs()
            yield d

    def add_child(self, tree):
        self.child.append(tree)
        tree.father = self

    def files(self):
        return [ item for item in self.child if item.type == 'file' ]

    def dirs(self):
        return [ item for item in self.child if item.type == 'dir' ]

    @staticmethod
    def from_dict(fullpath, content):
        this = DirectoryTree("dir", fullpath)
        for dir in content['dirs']:
            name, dircontent = dir
            if name.startswith('.'): continue
            this.add_child(DirectoryTree.from_dict(os.path.join(fullpath, name), dircontent))
        for file in content['files']: 
            if file.startswith('.'): continue
            this.add_child(DirectoryTree("file", os.path.join(fullpath, file)))
        return this

    def __eq__(self, other):
        return other.fullpath == self.fullpath

    def find_by_fullpath(self, fullpath):
        def _find(cur, fullpath):
            if fullpath == cur.fullpath: return cur
            for child in cur.child: 
                if fullpath.startswith(child.fullpath): 
                    return _find(child, fullpath)
        return _find(self, fullpath)

    def open_path(self, node):
        while node.father is not self: 
            node.father.is_open = True
            node = node.father

vim.command("""
function! RemoteFileCommandComplete(ArgLead, CmdLine, CursorPos)
    let leading = a:ArgLead
    let res = py3eval("Xiongkun.FileSystem().file_complete('" . leading . "')")
    return res
endfunction
""")


@vim_utils.Singleton
class FileSystem:
    def __init__(self):
        self.remount()

    def remount(self):
        self._last_error = ""
        self._is_remote = None
        self.cwd = None
        from .rpc import remote_project
        if remote_project is not None:
            print ("RemoteFileSystem Mounted.")
            self.prefix = ""
            self.cwd = remote_project.root_directory
            self._is_remote = True
            try:
                git_branch = ''.join(FileSystem().eval('git symbolic-ref --short HEAD 2>/dev/null'))
            except: 
                git_branch = "[no branch]"
            with vim_utils.VimVariableGuard(git_branch) as git_branch:
                vim.command(f"let g:current_branch={git_branch}")
            vim.command("AirlineRefresh!")
        else: 
            print ("localFileSystem Mounted.")
            self.prefix = ""
            self.cwd = vim.eval("getcwd()")
            self._is_remote = False
        if hasattr(self, "cached_tree"): 
            delattr(self, "cached_tree")

    def is_remote(self):
        return self._is_remote

    def last_error(self):
        return self._last_error

    def store(self, filepath, content):
        assert isinstance(content, (list, str))
        if isinstance(content, list):
            content = "\n".join(content)
        msg= rpc_wait("remotefs.store", filepath, content)
        if msg != "success": 
            self._last_error = msg
            return False
        return True

    def fetch(self, filepath):
        content = rpc_wait("remotefs.fetch", filepath)
        return content

    def abspath(self, filepath):
        if filepath.startswith("/"): return filepath
        else: return os.path.join(self.getcwd(), filepath)

    def bufname(self, filepath):
        abspath = self.abspath(filepath)
        return self.prefix + abspath

    def filepath(self, bufname):
        if bufname.startswith(self.prefix): 
            return bufname[len(self.prefix):]
        return bufname

    def bufload_file(self, filepath, force=False):
        filepath = self.abspath(filepath)
        def do_open(content): 
            tmp_file = vim_utils.TmpName()
            file = codecs.open(tmp_file, "w", "utf-8")
            file.write(content)
            file.close()
            bufnr = vim.eval(f'bufadd("{filepath}")')
            with vim_utils.CurrentBufferGuard():
                #vim.eval(f"setbufvar({bufnr}, '&buftype', 'acwrite')") # this option will make quickfix bugs.
                vim.eval(f"setbufvar({bufnr}, '&buflisted', 1)")
                vim.command(f"keepjumps noswap b {bufnr}")
                if len(content) > 1024*1024*10: 
                    vim.command("Large!")
                    vim.command("setlocal bufhidden=hide")
                vim.command(f"keepjumps normal ggdG")
                vim.command(f"keepjumps read {tmp_file}")
                vim.command("keepjumps normal ggdd")
                vim.command("set nomodified")
                timestamp = str(rpc_wait("remotefs.timestamp", filepath))
                vim.eval("setbufvar(bufnr(), 'remote', 'remote')")
                vim.eval(f"setbufvar(bufnr(), 'timestamp', '{timestamp}')")
                start_register_remote_write(bufnr)
            return bufnr
        exist = self.bufexist(filepath)
        if not exist or force : 
            if self.is_remote(): 
                content = FileSystem().fetch(filepath)
                bufnr = do_open(content)
            else: 
                bufnr = vim.eval(f'bufadd("{filepath}")')
                vim.command(f"noswapfile call bufload('{filepath}')")
            return bufnr
        else: 
            bufnr = vim.eval(f"bufnr('{filepath}')")
            assert bufnr != "-1"
            return bufnr

    def bufexist(self, file):
        if not IsBufferExist(file): return False
        if vim.eval(f"getbufvar('{file}', 'remote', '')") == '': 
            return not self._is_remote
        else: 
            return self._is_remote

    def list_dir(self, dirpath):
        return rpc_wait("remotefs.list_dir", dirpath)

    def file_complete(self, leading): 
        if not leading.startswith("/"):
            leading = os.path.join(self.getcwd(), leading)
        return rpc_wait("remotefs.file_complete", leading)

    def cd(self, dirpath):
        self.cwd = dirpath

    def glob(self, dirpath, pattern):
        pass

    def tree(self, dirpath=None):
        # return format:
        # DIR = {'files': [], 'dirs': DIR}
        if not hasattr(self, "cached_tree"):
            if not dirpath:
                dirpath = self.cwd
            results = rpc_wait("remotefs.tree", dirpath)
            self.cached_tree = DirectoryTree.from_dict(dirpath, results)
        return self.cached_tree

    def create_node(self, filepath):
        if filepath[-1] == '/': command = "mkdir"
        else: command = "touch"
        if hasattr(self, "cached_tree"): del self.cached_tree
        return self.command(f"{command} {filepath}")

    def remove_node(self, filepath):
        if hasattr(self, "cached_tree"): del self.cached_tree
        return self.command(f"rm -r {filepath}")
        

    def completer(self, cur_input):
        pass

    def exists(self, filepath):
        """ whether this file exist in remote filesystem.
        """
        return rpc_wait("remotefs.exists", filepath)

    def isfile(self, filepath):
        """ whether this file exist in remote filesystem.
        """
        return rpc_wait("remotefs.isfile", filepath)

    def isdir(self, filepath):
        """ whether this file exist in remote filesystem.
        """
        return rpc_wait("remotefs.isdir", filepath)

    def edit(self, filepath, force=False): 
        filepath = self.abspath(filepath)
        bufnr = FileSystem().bufload_file(filepath, force)
        GoToBuffer(bufnr, '.')

    def jumpto(self, location, method):
        GoToLocation(location, method)

    def command(self, command_str, block=True):
        try: 
            self.eval(command_str, block)
            return True
        except Exception as e: 
            print (f"Error while execute: {command_str}, {e}")
            return False

    def getcwd(self):
        return self.cwd

    def eval(self, command_str, block=True): 
        """ call bash command and get output 
            outputs is a list of string without '\n'
        """
        cwd = self.getcwd()
        command_str = f"cd {cwd} && " + command_str
        if block is True: 
            ret = rpc_wait("remotefs.eval", command_str)
            if ret['status'] == "ok":
                return ret['output']
            if ret['status'] == "error":
                raise RuntimeError(f"Eval Failed: {command_str} with error: {ret['error']}")
        else: 
            rpc_call("remotefs.eval", None, command_str)
            return True

    def create_temp_file(self, suffix=""):
        """ create a temp file and start to edit it.
        """
        filename = rpc_wait("remotefs.create_temp_file", suffix)
        return filename

    def edit_temp_file(self, suffix=""):
        """ create a temp file and start to edit it.
        """
        filename = self.create_temp_file(suffix)
        vim.command('tabe')
        self.edit(filename, force=True)

    def is_buffer_lastest(self, bufname=None):
        """ compare the timestamp of current buffer and remote file.
            return True if current buffer is the latest.
        """
        if not bufname: bufname = vim.eval("bufname()")
        filepath = self.abspath(bufname)
        current_timestamp = vim.eval(f"getbufvar('{bufname}', 'timestamp', '-1')")
        assert current_timestamp != -1
        stamp = str(rpc_wait("remotefs.timestamp", filepath))
        if stamp == current_timestamp: 
            return True
        return False

    def timestamp(self, filepath):
        if self.is_remote(): 
            stamp = str(rpc_wait("remotefs.timestamp", filepath))
            assert stamp != "-1"
            return stamp
        else:
            vim.command("echom 'timestamp is not supported in local mode.'")

    def git_based_path(self, filepath):
        abs_path = self.abspath(filepath)
        rel_path = str(rpc_wait("remotefs.git_based_path", abs_path))
        return rel_path

    def current_filepath(self):
        return self.filepath(vim.eval("bufname()"))
