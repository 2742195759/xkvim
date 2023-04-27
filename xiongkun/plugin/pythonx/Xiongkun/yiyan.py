import vim
import traceback
from . import vim_utils
import time
from .func_register import vim_register
import threading
import subprocess
from functools import partial
import re
from .log import log
import threading
from .vim_utils import VimWindow
from .rpc import rpc_call

class YiyanSession:
    def __init__(self):
        self._inited = False
        pass

    def init(self):
        if self._inited: 
            return 
        self.busy = False # wait for the yiyan output
        self.history = []
        self.buf_name = "yiyan"
        self.bufnr = None
        self._create_buffer()
        self._inited = True
        rpc_call("yiyan.init_yiyan", on_return=lambda x: None)

    def previous_input(self):
        last_input = self.history[-1][0]
        vim.eval(f'setbufline({self.bufnr}, "$", "yiyan> {last_input}")')

    def query(self, query):
        vim.eval(f"prompt_setprompt({self.bufnr}, '')")
        if self.busy: 
            return
        self.busy = True
        def on_return(outputs):
            self.busy = False
            vim.eval(f"prompt_setprompt({self.bufnr}, 'yiyan> ')")
            winnr = vim_utils.FindWindowInCurrentTabIf(
                lambda wnr: int(vim.eval(f"winbufnr({wnr})")) == int(self.bufnr))
            win_id = vim.eval(f"win_getid({winnr})")
            with vim_utils.CurrentWindowGuard(win_id):
                if outputs: 
                    ans = "".join(outputs)
                    self.history.append((query, ans))
                    for idx, ans in enumerate(outputs):
                        ans = vim_utils.escape(ans)
                        ans = ans.strip("\n")
                        vim.eval(f'appendbufline({self.bufnr}, line("$")-1, "{ans}")')
                else:
                    print("Yiyan error happens, restart please.:\n1. Navigation Timeout Exceeded: 30000 ms exceeded.")
                    ans = "[Connection Fail]: Please retry."
                    self.history.append((query, ""))
                    vim.eval(f'appendbufline({self.bufnr}, line("$")-1, "{ans}")')
            # when in insert mode, the inputs don't startswith "yiyan>", a new 
            # line will be inserted, so we need a <space> to disable a new line.
            vim.command('exec "normal gi "') 
        rpc_call("yiyan.query", on_return, query)

    def _create_buffer(self):
        self.bufnr = vim.eval(f"bufadd('{self.buf_name}')")
        with vim_utils.CurrentBufferGuard(self.bufnr):
            vim.command("set filetype=")
            vim.command("set syntax=yiyan")
            vim.command("setlocal bufhidden=hide")
            vim.command("setlocal buftype=prompt")
            vim.command("nnoremap <f7> <cmd>YiyanTrigger<cr>")
            vim.command("inoremap <f7> <cmd>YiyanTrigger<cr>")
            vim.command("imap <up> <cmd>YiyanLastInput<cr>")
            vim.command("setlocal fdc=0")
            vim.command("setlocal wrap")
            vim.eval(f"prompt_setprompt(bufnr(), 'yiyan> ')")
            vim.command("""
function! YiyanQuery(text)
    call PyQuery_yiyan(a:text)
endfunction
""")
            vim.eval(f"prompt_setcallback(bufnr(), 'YiyanQuery')")
            vim.command("setlocal nofoldenable")

    def show(self):
        winnr = vim_utils.FindWindowInCurrentTabIf(
            lambda wnr: int(vim.eval(f"winbufnr({wnr})")) == int(self.bufnr))
        if winnr == -1:
            vim.command("botright new")
            vim.command("resize 12")
            vim.command(f"b {self.bufnr}")
            vim.command("startinsert!")
        else: 
            #vim_utils.GoToWindow(winnr)
            self.hide()

    def hide(self):
        winnr = vim_utils.FindWindowInCurrentTabIf(
            lambda wnr: int(vim.eval(f"winbufnr({wnr})")) == int(self.bufnr))
        win_id = vim.eval(f"win_getid({winnr})")
        with vim_utils.CurrentWindowGuard(win_id): 
            vim.command(":q")

session = YiyanSession()

@vim_register(command="Yiyan", with_args=True)
def query_yiyan(args):
    if len(args) == 0 or "".join(args).strip() == "": 
        return 
    log("Yiyan query: ", args)
    session.init()
    session.query("".join(args))

@vim_register(command="YiyanLastInput")
def yiyan_last_input(args):
    session.init()
    session.previous_input()

@vim_register(command="YiyanTrigger", keymap="<f7>")
def yiyan_trigger(args):
    assert len(args) == 0
    session.init()
    session.show()

#@vim_register(command="YiyanCodeUI", keymap="<f7>")
#def yiyan_code(args):
    #from .buf_app_translate import TranslatorBuffer
    #assert len(args) == 0
    #def on_return(outputs):
        #if len(outputs) == 0: 
            #print("Retry.")
        #else: 
            #print("")
    #rpc_call("yiyan.query", on_return, query)