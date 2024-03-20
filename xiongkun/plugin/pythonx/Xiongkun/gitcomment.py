import vim
import sys
import os
import os.path as osp
from .func_register import *
from .vim_utils import *
from .buf_app import *
from .remote_machine import RemoteConfig
from .remote_fs import FileSystem
import re

def OpenPR(pr_str):#{{{
    pr_str = str(pr_str)
    url = None
    url_first = None
    for line in FileSystem().eval("git remote -v"):
        line = line.split(' ')[0].strip()
        field = line.split("\t")
        if field[0] == 'upstream': 
            url_first = field[1]
            break
    if url_first is None: 
        print("git remote -v can't found upsteam.")
        return
    if url_first.endswith('.git'): url_first = url_first[:-4]
    url = f'{url_first}/pull/{pr_str}'
    RemoteConfig().get_machine().chrome(url) #}}}

def _ParsePR(filepath, line_nr):#{{{
    blames = GetGitComment(filepath, line_nr)
    commit_id, info, content, comment = blames[0]
    import re
    searched = re.search("\(#(\d+)\)", "".join(comment))
    if searched is not None: 
        return searched.group(1)
    raise Exception("Not found PR information")
    #}}}

def GetGitComment(filepath, line_nr):#{{{
    """GetGitComment from filepath and line number
    """
    lines = FileSystem().eval(f'git blame -L{line_nr},{line_nr} -- {filepath}')
    blames = []
    for line in lines:
        commit_id = line.split('(')[0].strip()
        if commit_id[0] == '^': commit_id = commit_id[1:]
        commit_id = commit_id.split(' ')[0].strip()
        others = '('.join(line.split('(')[1:])
        info = others.split(')')[0]
        content = ')'.join(others.split(')')[1:])
        comment = FileSystem().eval("git show -q %s " % commit_id)
        blames.append([commit_id, info, content, comment])
    return blames
    #}}}

@vim_register(command="GG", action_tag="git blame")
def ShowGitComment(args):#{{{
    """
    `GG`: show git comment of current line
    >>> GG
    """
    try:
        filepath = CurrentEditFile()
        line_nr = GetCursorXY()[0]
        blames =  GetGitComment(filepath, line_nr)
        for commit_id, info, content, comment in blames:
            for line in comment:
                line = escape(line, "\"")
                vim.command('echom "' + line + '"')
    except Exception as e:
        print (f"Error : {e}")
        #vim.command('echoerr ' + '"Not Commit Yet"')#}}}

@vim_register(command="GO")
def GitOpenInBrowser(args):#{{{
    try:
        filepath = CurrentEditFile()
        line_nr = GetCursorXY()[0]
        pr_str = _ParsePR(filepath, line_nr)
        OpenPR(pr_str)
    except Exception as e:
        print (f"Error : {e}")

def GitDiffFiles(commit_id=None, filename=None):
    """ if args is None: diff current file with HEAD
        else if: len(args) == 1:
            diff currentfile with args[0](COMMIT_ID)
        else if: len(args) == 2:
            diff currentfile with args[0](COMMIT_ID):args[1]FILENAME
    """
    if filename is None: filename = CurrentEditFile(abs=True)
    if commit_id is None: commit_id = "HEAD"
    filename = FileSystem().git_based_path(filename)
    if not filename: 
        print (f"File {filename} not in a git project. Ensure you are in a git project.")
        return 
    filetype = vim.eval("&ft")
    tmpfile = FileSystem().create_temp_file()
    if FileSystem().command("git show %s:%s > %s" % (commit_id, filename, tmpfile)) is False:
        return
    vim.command("wincmd T")
    vim.command("vertical split")
    vim.command("set nofoldenable")
    vim.command("wincmd w")
    FileSystem().edit(tmpfile, True)
    vim.command(f"setlocal filetype={filetype}")
    vim.command("set nofoldenable")
    vim.eval('feedkeys("\\<cmd>windo diffthis\\<cr>")')

def GitDiffRecentChangesGivenWindows(commit_ids, window_ids, filename):#{{{
    """ Diff commit_ids[0]:filename and commit_ids[1]:filename in windows.
    """
    filetype = GetFileTypeByName(filename)
    for wid, cid in zip(window_ids, commit_ids):
        with CurrentWindowGuard(wid):
            vim.command('setlocal modifiable')
            cmd = "0read! git show %s:%s" % (cid, filename)
            vim.command(f"echom '{cmd}'")
            vim.eval("win_execute({wid}, \"{cmd}\", \"silent!\")".format(
                wid=wid, cmd=cmd
            ))
            if filetype: vim.command(f'setlocal filetype={filetype}')
            vim.command("setlocal foldmethod=diff")
            memory_buffer()
            vim.command('diffthis')#}}}

@vim_register(command="Diff", with_args=True, action_tag="git diff")
def DiffCurrentFile(args):#{{{
    """
    `Diff`: show git diff of current file vs HEAD.
    Usage : Diff [COMMITID] [FILENAME]
    >>> Diff                # current file and HEAD
    >>> Diff a9ty6          # current file and commit a9ty6
    >>> Diff a9ty6 vimrc    # vimrc file vs commit a9ty6
    """
    commit_id = None
    filename = None
    if len(args) == 1 : 
        commit_id = args[0]
        filename = None
    elif len(args) == 2 : 
        commit_id = args[0]
        filename = args[1]
    GitDiffFiles(commit_id, filename)#}}}

class GitDiffLayout(Layout):#{{{
    """
    create windows for diff: ['files', 'first', 'second'] and show diff between first and second.
    """
    # ------------------------
    # |       files          |
    # ------------------------
    # | first     |  second  |
    # ------------------------
    def __init__(self, new_tabe=False, file_tab=True):
        super().__init__("first")
        self.new_tabe = new_tabe
        self.file_tab = file_tab
        
    def _create_windows(self):
        if self.new_tabe: 
            vim.command("tabe")
            vim.command(f"new ")
            vim.command(f"resize 8")
            vim.command("wincmd j") # close all other windows
            vim.command(f"vne ")
        filewin = vim.eval("win_getid(1)")
        wins = [vim.eval("win_getid(2)"), vim.eval("win_getid(3)")]
        ret = {"files": filewin, "first": wins[0], "second": wins[1]}
        if not self.file_tab:
            with CurrentWindowGuard(filewin): 
                vim.command("q")
            del ret['files']
        return ret#}}}

class GitFileCommitLogBuffer(BashCommandResultBuffer): #{{{
    def __init__(self, command_getter, ondiff): 
        """ ondiff: callback when diff is triggled.
                    => function(commit0, commit1)
        """
        cmd = command_getter()
        super().__init__(cmd, "git")
        self.ondiff = ondiff

    def _open(self):
        cur_pr, prev_commit = self._parse_info()
        if cur_pr: OpenPR(cur_pr)
        else: 
            print("Don't find PR information")

    def _next(self, forward=True):
        if forward: 
            vim.command('execute "normal /^commit\<cr>zz"')
        else: 
            vim.command('execute "normal ?^commit\<cr>zz"')

    def keymap_func(self, key):
        if key == "j": self._next(True)
        if key == "k": self._next(False)
        if key == '<enter>': self._diff()
        if key == 'o': self._open()

    def get_keymap(self):
        sets = [ 'j', 'k', '<enter>', 'o' ]
        ret = {}
        for s in sets:
            ret[s] = GitFileCommitLogBuffer.keymap_func
        return ret

    def _parse_info(self):
        lines = GetAllLines(self.bufnr)
        cur = GetCursorXY()[0] - 1
        prev_commit = None
        pr = None
        for i in range(cur+1, len(lines)):
            if lines[i].startswith("commit"): 
                prev_commit = lines[i].strip().split(' ')[1]
                break
            try:
                pr = re.search("\(#(\d+)\)", lines[i]).group(1)
            except:
                pass
        return pr, prev_commit

    def _diff(self):
        commit = GetCurrentLine().split(' ')[1]
        cur_pr, prev_commit = self._parse_info()
        prev_commit = FileSystem().eval("git log {commit}^ -1 | head -n1 | cut -d' ' -f2".format(commit=commit))[0].strip()
        if prev_commit is None: return 
        self.ondiff(commit, prev_commit)
#}}}

class GitFileSelector(BashCommandResultBuffer): #{{{
    def __init__(self, cmd, onenter): 
        """ function(line: str, files=boolean)
        """
        super().__init__(cmd, "nerdtree")
        self.onenter = onenter

    def get_keymap(self):
        sets = [ '<enter>' ]
        ret = {'<enter>': lambda x, y: self.onenter(GetCurrentLine().strip(), False)}
        return ret
#}}}

class DiffBuffer(BashCommandResultBuffer):
    def __init__(self, cmd, filetype, file):
        super().__init__(cmd,filetype)
        self.file = file
    def get_keymap(self):
        """ some special key map for example.
        """
        def fff(x, y):
            x, y = GetCursorXY()
            vim.command(f"tabe {self.file}")
            vim.command(f":{x}")
        return {
            '<enter>': lambda x,y: fff(x, y)
        }

class GitPreviewApp(Application):#{{{
    def __init__(self, command_getter, init_file=None, commit_list=[]):
        """
        """
        super().__init__()
        self.command_getter = command_getter
        self.init_file = init_file

        def ondiff(commit0, commit1): 
            """ while press "d" in the git file log buffer.
            """
            if self.git_diff_layout is None: 
                self.git_diff_layout = GitDiffLayout(True, True)
                self.git_diff_layout.create()

            def onenter(file=None, files=False):
                diff_files_cmd = f"git diff {commit0} {commit1} | grep 'diff --git' | cut -d' ' -f3 | cut -c3- | uniq -u"
                self.git_diff_files.create(GitFileSelector(diff_files_cmd, onenter))

                filetype = GetFileTypeByName(file) if file else None
                bufs = [self.git_diff_0, self.git_diff_1]
                commits = [commit0, commit1]
                for buf, commit in zip(bufs, commits): 
                    cmd = "git show %s:%s" % (commit, file) if file else "echo 'Please Specify a file'"
                    buf.create(DiffBuffer(cmd, filetype, file))
                bufdict = {
                    'files': self.git_diff_files.get(), 
                    'first': self.git_diff_0.get(), 
                    'second': self.git_diff_1.get(),
                }
                if not files: del bufdict['files']
                self.git_diff_layout.reset_buffers(bufdict)
                self.git_diff_layout.windiff(['first', 'second'])

            onenter(file=init_file, files=True)

        self.git_diff_layout = None
        self.git_log_layout = CreateWindowLayout(active_win='win')
        self.git_log_buf = GitFileCommitLogBuffer(self.command_getter, ondiff)

        self.git_diff_0 = BufferSmartPoint()
        self.git_diff_1 = BufferSmartPoint()
        self.git_diff_files = BufferSmartPoint()
        self.on_diff = ondiff
        self.commit_list = commit_list

    def start(self):
        if len(self.commit_list) == 0: 
            # select by user.
            self.git_log_buf.create()
            self.git_log_layout.create({'win': self.git_log_buf})
        else:
            assert len(self.commit_list) == 2, "Must be call with 2 commit_list."
            self.on_diff(*self.commit_list)
#}}}

@vim_register(command="GF", with_args=True, action_tag="git history")
def GitFileHistory(args):
    """ 
    ## Overview
    1. 打开一个新的窗口，显示当前文件的git历史
    2. 支持再里面进行展示文件显示：
      ------------------------
      |       files          |
      ------------------------
      | first     |  second  |
      ------------------------

    ## Usage
    GF [<author>]

    >>> GF xiongkun03
    >>> GF
    ## Description
    1. 如果GF没有参数，打印所有的 commit
    2. 如果GF带author参数，打印所有Authro的commit
    """
    command_getter  = None
    init_file = None
    if len(args) == 0: 
        """ show all git log which modified this file.
        """
        def file_log_command():
            file = CurrentEditFile()
            vim.command(f"echom '{file}'")
            return f"git log {file}" 
        command_getter = file_log_command
        init_file = CurrentEditFile()
    elif len(args) == 1: 
        """ show all git log belongs to certain author.
        """
        author = args[0]
        def author_log_command():
            print (f"Author is {author}")
            return f"git log --author {author}" 
        command_getter = author_log_command
        init_file = None

    app = GitPreviewApp(command_getter, init_file)
    app.start()

@vim_register(command="GDiff", with_args=True, action_tag="git diff two commit")
def GitDiffCommit(args):
    """ 
    ## Overview
    1. 打开一个新的窗口，显示当前文件的git历史
    2. 支持再里面进行展示文件显示：
      ------------------------
      |       files          |
      ------------------------
      | first     |  second  |
      ------------------------

    ## Usage
    GDiff [first_commit/branch] [second_commit/branch]

    >>> GDiff 3620947dfa9dd106698c17bca45b17815bc62a6a
    >>> GDiff HEAD 3620947dfa9dd106698c17bca45b17815bc62a6a
    ## Description
    1. 如果GDiff一个参数，对比 HEAD vs commit
    2. 如果GDiff两个参数，对比 commit1 vs commit2
    """
    init_file = None
    init_file = CurrentEditFile()
    commit_list = []
    if len(args) == 0: 
        print("Please Input 1/2 arguments.")
        return 
    elif len(args) == 1: 
        commit_list.append("".join(FileSystem().eval("git rev-parse HEAD")).strip())
        commit_list.append(args[0])
    elif len(args) == 2: 
        commit_list.append(args[0])
        commit_list.append(args[1])
    app = GitPreviewApp(lambda:"no command", init_file, commit_list)
    app.start()
