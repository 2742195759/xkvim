from ..vim_utils import *
from ..func_register import vim_register
from ..remote_machine import remote_machine_guard, RemoteConfig
from ..log import debug

@vim_register(command="MarkdownPreviewStart", action_tag="markdown_preview")
def MarkdownPreviewStart(args):
    """
    `MarkdownPreviewStart`: start markdown preview in remote machine.
    -----------------------------------------------------------------
    Usage:
    >>> MarkdownPreviewStart
    """
    filepath = CurrentEditFile(True)
    vim.command("PreviewFile %") # open browser windows and show the markdown -- typora is the best choices.
    vim.command("set updatetime=300")
    vim.command("set wrap")
    commands(""" 
augroup MarkdownPreviewGroup
    autocmd!
    autocmd BufWriteCmd *.md,*.markdown MarkdownPreviewUpdate
    autocmd CursorHold *.md,*.markdown MarkdownSetCursor
augroup END
    """)
    #autocmd CursorMoved *.md,*.markdown MarkdownSetCursor

@vim_register(command="MarkdownPreviewUpdate")
def MarkdownPreviewUpdate(args):
    vim.command("SendFile %")
    vim.command("Tabular /|/c1")
    vim.command("MarkdownSetCursor")

@vim_register(command="MarkdownSetCursor")
def SendCursor(args):
    """
    SendCursor: send cursor position to remote machine.
    ---------------------------------------------------
    Usage:
    >>> MarkdownSetCursor
    """
    # OS only currently
    line, col = GetCursorXY()
    while line > 1 :
        if GetLine(line).strip() in ['', '```']: line -= 1
        else: break
            
    if RemoteConfig().get_remote() == "mac": 
        set_cursor_file = "/Users/xiongkun03/project/marktext/marktext_set_cursor.js "
    elif RemoteConfig().get_remote() == "pc": 
        set_cursor_file = "C:/Users/xiongkun/Desktop/linux/marktext-for-vim/marktext_set_cursor.js"
    else: 
        raise NotImplementedError("Only support mac currently.")
    RemoteConfig().get_machine().execute(f"node {set_cursor_file} {line-1} {1000}", block=False)

@vim_register(command="PaddleAutoSyncMode", action_tag="paddle auto sync")
def PaddleAutoSync(args):
    """
    `PaddleAutoSync`: start auto sync paddle python file between build and local.
    -----------------------------------------------------------------
    Usage:
    >>> PaddleAutoSyncMode
    """
    commands(""" 
augroup PaddleAutoSync
    autocmd!
    autocmd BufWriteCmd *.py SyncBuild
augroup END
    """)
    #autocmd CursorMoved *.md,*.markdown MarkdownSetCursor

@vim_register(command="EndPaddleAutoSyncMode", action_tag="end paddle auto sync")
def EndPaddleAutoSync(args):
    commands(""" 
augroup PaddleAutoSync
    autocmd!
augroup END
    """)

