import vim
import sys
import os
def func():
    return 0

def GetGitComment(filepath, line_nr):
    """GetGitComment from filepath and line number

    :filepath: TODO
    :line_nr: TODO
    :returns: TODO

    """
    gitblame = os.popen('git blame ' + filepath)
    lines = gitblame.readlines()
    line = lines[line_nr-1]
    commit_id = line.split('(')[0].strip()
    others = '('.join(line.split('(')[1:])
    info = others.split(')')[0]
    content = ')'.join(others.split(')')[1:])
    comment = os.popen("git log --pretty=format:'%Cred%h%Creset -%C(yellow)%d%Creset %s %Cgreen(%cr)%Creset' --abbrev-commit --date=relative" + 
        '| grep ' + commit_id)
    comment = str(comment.read())
    return commit_id, info, content, comment

def ShowGitComment(filepath, line_nr):
    commit_id, info, content, comment = GetGitComment(filepath, line_nr)
    vim.command('echom "' + info + '"') 
    vim.command('echom "' + comment + '"')
    
