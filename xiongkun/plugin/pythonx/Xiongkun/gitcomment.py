import vim
import sys
import os
import os.path as osp
from .func_register import *
from .vim_utils import *

def get_git_related_path(abspath):
    def is_git_director(current):
        return osp.isdir(current) and osp.isdir(osp.join(current, ".git"))
    abspath = osp.abspath(abspath)
    origin = abspath
    while not is_git_director(abspath): 
        abspath = osp.dirname(abspath)
    if abspath in ['/', '~']: 
        print ("Can find git in father directory.")
    return origin[len(abspath):].strip("/")

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

def ShowGitComment(filepath, line_nr):
    try:
        commit_id, info, content, comment = GetGitComment(filepath, line_nr)
        comment = comment.split('\n')
        for line in comment:
            vim.command('echom "' + line + '"')
    
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
