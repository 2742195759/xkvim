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
from .rpc import rpc_call, RPCServer
from .windows import MessageWindow

__yiyan_server = None
def yiyan_server():
    global __yiyan_server
    if __yiyan_server is None: 
        __yiyan_server = RPCServer("Yiyan", "host.docker.internal:8888", "yiyan", function="Xiongkun.yiyan_server()")
    return __yiyan_server

class YiyanResponsePostProcessor:
    def __init__(self, outputs):
        self.outputs = outputs

    def get_first_code(self):
        """ get code line from yiyan response.
            return: [str], without \n.
        """
        class YiyanCode: 
            def __init__(self, code, language):
                self.code = code
                self.language = language

        start = False
        code = []
        lang = None
        for line in self.outputs:
            line = line.rstrip()
            match = re.match(r"```[a-z]*$", line) # match for ``` and ```python
            if match:
                start = not start
                if start == False: break
                lang = line.split("```")[-1].strip()
                continue
            if start: 
                code.append(line)
        return YiyanCode(code, lang)

    def is_error(self):
        if self.outputs: return False
        return True

    def get_outputs(self):
        return self.outputs

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
            yiyan_server().call("yiyan.query", on_return, query)

    def _create_buffer(self):
        self.bufnr = vim.eval(f"bufadd('{self.buf_name}')")
        with vim_utils.CurrentBufferGuard(self.bufnr):
            vim.command("setlocal noswapfile")
            vim.command("set filetype=")
            vim.command("setlocal buftype=nofile")
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

@vim_register(with_args=True)
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

def yiyan_converse(query, query_process_fn=None, return_process_fn=None, accept_fn=None): 
    def on_return(outputs):
        package = YiyanResponsePostProcessor(outputs)
        if not package.is_error(): 
            context, syntax = return_process_fn(package)
            assert isinstance(context, str), "Context must be string."
            if len(context): 
                MessageWindow().display_message(context, syntax=syntax)
                MessageWindow().doc_buffer.execute("setlocal wrap")
                MessageWindow().doc_buffer.execute("setlocal nu")
                MessageWindow().set_extra((package, accept_fn))
                vim.command("set mouse=a")
            else:
                MessageWindow().display_message("没有代码.", 10)
        else:
            MessageWindow().display_message("Error happens, please retry later.", 10)
        
    if query_process_fn:  
        query = query_process_fn(query)
    MessageWindow().display_message("等待文心一言...") 
    yiyan_server().call("yiyan.query", on_return, query)


@vim_register(command="Yiyan", with_args=True)
def yiyan_query(args):
    assert len(args) > 0
    query = "".join(args)
    def context_filter(package):
        return "\n".join(package.get_outputs()), "yiyan"
    yiyan_converse(query, None, context_filter)


@vim_register(command="YiyanCode", with_args=True)
def yiyan_code(args):
    assert len(args) > 0
    query = "".join(args)
    prefix_query = "只输出一段完整代码, "
    query = prefix_query + query
    def code_filter(package):
        code = package.get_first_code()
        return "\n".join(code.code), code.language
    yiyan_converse(query, None, code_filter)

def guess_indent(lines):
    if len(lines) == 0: return 0
    return len(lines[0]) - len(lines[0].lstrip())

@vim_register(command="YiyanRewrite", with_args=True)
def yiyan_code_rewrite(args):
    word = vim_utils.GetVisualWords()
    word = word.rstrip()
    lines = word.split("\n")
    lines = [ "<cr>" if line=="" else line for line in lines ]
    indent = guess_indent(lines)
    word = "\n".join(lines)
    assert len(args) > 0
    query = "".join(args)
    query = query.strip()
    query = "只输出一段完整代码, 按要求改写下面代码：\n要求: " + query + "\n代码:\n"
    query += word
    def code_filter(package):
        return "\n".join(package.get_outputs()), "yiyan"
    def accept_fn(package):
        code = package.get_first_code().code
        code = [ " " * indent + line for line in code ]
        code = "\n".join(code)+"\n"
        vim.command("normal gvd`<")
        vim_utils.insert_text(code)
    yiyan_converse(query, None, code_filter, accept_fn)


@vim_register(command="YiyanCodeAccept")
def yiyan_code_accept(args):
    package, accept_fn = MessageWindow().get_extra()
    if accept_fn is None:
        code = "\n".join(package.get_first_code().code)
        vim_utils.insert_text(code)
    else:
        accept_fn(package)
    MessageWindow().hide()
    vim.command("set mouse=")

