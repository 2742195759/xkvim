from ..vim_utils import *
from ..func_register import vim_register
from ..remote_machine import remote_machine_guard, RemoteConfig
from ..log import debug

@vim_register(command="XelatexMode", action_tag="xelatex mode")
def XelatexEditMode(args):
    """
    `XelatexEditMode`: start xelatex mode in vim. 
    1. auto switch im-select: https://github.com/daipeihust/im-select
    2. activate some abbreviate used in xelatex.
    3. compiling when save.
    -----------------------------------------------------------------
    Usage:
    >>> XelatexMode
    """
    commands(""" 
augroup XelatexMode
    autocmd!
    autocmd InsertLeave * SwitchInputMethod com.apple.keylayout.ABC
    autocmd InsertEnter * SwitchInputMethod com.apple.inputmethod.SCIM.ITABC
augroup END
    """)
    #autocmd CursorMoved *.md,*.markdown MarkdownSetCursor

@vim_register(command="EndXelatexMode", action_tag="end xelatex mode")
def EndPaddleAutoSync(args):
    commands(""" 
augroup XelatexMode
    autocmd!
augroup END
    """)

@vim_register(command="SwitchInputMethod", with_args=True)
def SwitchInputMethod(args):
    remote_machine_guard("mac")
    RemoteConfig().get_machine().execute(f"/opt/homebrew/Cellar/im-select/1.0.1/bin/im-select {args[0]}")
