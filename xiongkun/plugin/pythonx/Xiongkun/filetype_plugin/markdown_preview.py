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

@vim_register(command="MarkdownPreviewUpdate")
def MarkdownPreviewUpdate(args):
    vim.command("SendFile %")
