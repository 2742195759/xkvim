import vim
import sys
import os
import os.path as osp
from .func_register import *
from .vim_utils import *
from .converse_plugin import open_url_on_mac
from .buf_app import *
import re

def OpenPR(pr_str):#{{{
    pr_str = str(pr_str)
    url = None
    url_first = None
    for line in str(os.popen("git remote -v").read()).split("\n"): 
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
    open_url_on_mac(url)#}}}

def _ParsePR(filepath, line_nr):#{{{
    commit_id, info, content, comment = GetGitComment(filepath, line_nr)
    import re
    return re.search("\(#(\d+)\)", comment).group(1)#}}}

def GetGitComment(filepath, line_nr):#{{{
    """GetGitComment from filepath and line number
    """
    gitblame = os.popen('git blame ' + filepath)
    lines = gitblame.readlines()
    line = lines[line_nr-1]
    commit_id = line.split('(')[0].strip()
    if commit_id[0] == '^': commit_id = commit_id[1:]
    others = '('.join(line.split('(')[1:])
    info = others.split(')')[0]
    content = ')'.join(others.split(')')[1:])
    comment = os.popen("git show %s -q" % commit_id)
    comment = str(comment.read())
    return commit_id, info, content, comment#}}}

@vim_register(command="GG")
def ShowGitComment(args):#{{{
    try:
        filepath = CurrentEditFile()
        line_nr = GetCursorXY()[0]
        commit_id, info, content, comment = GetGitComment(filepath, line_nr)
        comment = comment.split('\n')
        for line in comment:
            vim.command('echom "' + line + '"')
    except:
        vim.command('echoerr ' + '"Not Commit Yet"')#}}}

@vim_register(command="GO")
def GitOpenInBrowser(args):#{{{
    try:
        filepath = CurrentEditFile()
        line_nr = GetCursorXY()[0]
        pr_str = _ParsePR(filepath, line_nr)
        OpenPR(pr_str)
    except:
        vim.command('echoerr ' + '"Not Commit Yet"')#}}}

def GitDiffFiles(commit_id=None, filename=None):#{{{
    """ if args is None: diff current file with HEAD
        else if: len(args) == 1:
            diff currentfile with args[0](COMMIT_ID)
        else if: len(args) == 2:
            diff currentfile with args[0](COMMIT_ID):args[1]FILENAME
    """
    if filename is None: filename = CurrentEditFile(abs=True)
    if commit_id is None: commit_id = "HEAD"
    filename = get_git_related_path(filename)
    suffix = os.path.splitext(filename)[-1]
    tmp = TmpName() + suffix
    os.system("git show %s:%s > %s" % (commit_id, filename, tmp))
    vim.command("wincmd T")
    vim.command("vertical diffs %s" % tmp)
    vim.command("wincmd R")
    vim.command("wincmd w")#}}}

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

@vim_register(command="Diff", with_args=True)
def DiffCurrentFile(args):#{{{
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
        prev_commit = vim.eval("system(\"git log {commit}^ -1 | head -n1 | cut -d' ' -f2\")".format(commit=commit)).strip()
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
    def __init__(self, command_getter, init_file=None):
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

    def start(self):
        self.git_log_buf.create()
        self.git_log_layout.create({'win': self.git_log_buf})
#}}}

@vim_register(command="GF", with_args=True)
def GitFileHistory(args):#{{{
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
#}}}

@vim_register(command="Git", with_args=True)
def GitCommand(args):#{{{
    assert len(args) > 0, "Git push | commit"
    assert args[0] in ['push', 'commit']
    if args[0] == 'push':
        system("~/xkvim/bash_scripts/git_push.sh")
#}}}



