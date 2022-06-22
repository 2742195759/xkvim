import vim
import sys
import os
import os.path as osp
from .func_register import *
from .vim_utils import *
from .converse_plugin import open_url_on_mac

def OpenPR(pr_str):
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
    url = f'{url_first}/pull/{pr_str}'
    open_url_on_mac(url)

def _ParsePR(filepath, line_nr):
    commit_id, info, content, comment = GetGitComment(filepath, line_nr)
    import re
    return re.search("\(#(\d+)\)", comment).group(1)

def GetGitComment(filepath, line_nr):
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
    return commit_id, info, content, comment

@vim_register(command="GG")
def ShowGitComment(args):
    try:
        filepath = CurrentEditFile()
        line_nr = GetCursorXY()[0]
        commit_id, info, content, comment = GetGitComment(filepath, line_nr)
        comment = comment.split('\n')
        for line in comment:
            vim.command('echom "' + line + '"')
    except:
        vim.command('echoerr ' + '"Not Commit Yet"')

@vim_register(command="GO")
def GitOpenInBrowser(args):
    try:
        filepath = CurrentEditFile()
        line_nr = GetCursorXY()[0]
        pr_str = _ParsePR(filepath, line_nr)
        OpenPR(pr_str)
    except:
        vim.command('echoerr ' + '"Not Commit Yet"')

def GitDiffFiles(commit_id=None, filename=None):
    """ if args is None: diff current file with HEAD
        else if: len(args) == 1:
            diff currentfile with args[0](COMMIT_ID)
        else if: len(args) == 2:
            diff currentfile with args[0](COMMIT_ID):args[1]FILENAME
    """
    if filename is None: filename = CurrentEditFile()
    if commit_id is None: commit_id = "HEAD"
    filename = get_git_related_path(filename)
    #print("Filename:", filename)
    suffix = os.path.splitext(filename)[-1]
    tmp = TmpName() + suffix
    os.system("git show %s:%s > %s" % (commit_id, filename, tmp))
    vim.command("wincmd T")
    vim.command("vertical diffs %s" % tmp)
    vim.command("wincmd R")
    vim.command("wincmd w")

@vim_register(command="Diff", with_args=True)
def DiffCurrentFile(args):
    commit_id = None
    filename = None
    if len(args) == 1 : 
        commit_id = args[0]
        filename = None
    elif len(args) == 2 : 
        commit_id = args[0]
        filename = args[1]
    GitDiffFiles(commit_id, filename)
