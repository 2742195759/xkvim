import vim
import sys
import os
def func():
    return 0

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
