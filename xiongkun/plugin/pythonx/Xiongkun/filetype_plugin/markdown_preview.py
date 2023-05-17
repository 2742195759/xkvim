from ..vim_utils import *
from ..func_register import vim_register
from ..remote_machine import remote_machine_guard, RemoteConfig

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
    commands(""" 
augroup MarkdownPreviewGroup
    autocmd!
    autocmd BufWritePost *.md,*.markdown MarkdownPreviewUpdate
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
    if RemoteConfig().get_remote() == "mac": 
        set_cursor_file = "/Users/xiongkun03/project/marktext/marktext_set_cursor.js "
    else: 
        raise NotImplementedError("Only support mac currently.")
    RemoteConfig().get_machine().execute(f"node {set_cursor_file} {line-1} {10000}", block=False)
