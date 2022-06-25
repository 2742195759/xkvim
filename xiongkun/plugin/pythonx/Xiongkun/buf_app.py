import vim
import sys
import os
import os.path as osp
from .func_register import *
from .vim_utils import *

@vim_register(name="BufApp_KeyDispatcher")
def Dispatcher(args):
    """ args[0] ==  name
        args[1] ==  key_name
    """
    obj = Buffer.instances[args[0]]
    key = args[1]
    obj.keymap[key](obj, key)
    return True

def WindowQuit(name):
    obj = Buffer.instances[name]
    obj.delete()


class Buffer:
    instances = {}
    number = 0
    def __init__(self, appname, history=None, options=None):
        """
        options: 
            name = str: the name of application
            syntax = filepath
            clean  = [true] boolean, is clear all addtion keymap.
            vimopt = {
                key: value
            }
        """
        self.options = options if options else {}
        self.appname = appname
        self.name = appname + self._name_generator()
        self.keymap = self.get_keymap()
        self.history = history
        Buffer.instances[self.name] = self

    def get_keymap(self):
        return {}

    def _name_generator(self):
        Buffer.number += 1
        return str(Buffer.number)

    def save(self):
        """ return the history to save.
        """
        return None

    def onrestore(self, history):
        """ restore object by history.
        """
        pass

    def _clear(self):
        with CurrentBufferGuard(self.bufnr):
            vim.command("execute 'normal! ggdG'")
    
    def _put_string(self, text):
        text = escape(text)
        vim.eval(f"setbufline({self.bufnr}, 1, \"{text}\")")

    def onredraw(self):
        pass
    
    def oninit(self):
        pass

    def redraw(self):
        vim.command('setlocal modifiable')
        self.onredraw()
        vim.command('setlocal nomodifiable')
        self.after_redraw()

    def onwipeout(self):
        pass

    def _set_default_options(self):
        vim.command("set filetype=")
        vim.command("set syntax=")
        vim.command("setlocal bufhidden=hide")
        vim.command('setlocal nomodifiable')
        vim.command("setlocal buftype=nofile")
        vim.command("setlocal nofoldenable")

    def create(self):
        self._create_buffer()
        with CurrentBufferGuard(self.bufnr):
            if self.history: 
                self.onrestore(self.history)
            self._set_keymap()
            self._set_syntax()
            # custom initialized buffer options.
            self._set_autocmd()
            self._set_default_options()
            self.oninit()
            self.redraw()
        return self

    def after_redraw(self):
        pass

    def delete(self):
        self._unset_autocmd()
        self.onwipeout()
        with CurrentBufferGuard(self.bufnr): 
            tmp = vim.eval("bufadd(\"tmp\")")
            vim.command(f"b {tmp}")
            vim.command(f"bwipeout {self.bufnr}")
        del Buffer.instances[self.name]
        #vim.command(f"echom {name} is Quit. len(instances) is {len(Buffer.instance)}")

    def _unset_autocmd(self):
        vim.command(f"augroup {self.name}")
        vim.command(f"au!")
        vim.command(f"augroup END")

    def _set_autocmd(self):
        vim.command(f"augroup {self.name}")
        vim.command(f"au!")
        #vim.command(f"au BufHidden {self.name} py3 Xiongkun.WindowQuit('{self.name}')")
        #vim.command(f"au BufHidden {self.name} echo 'yes'")
        vim.command(f"augroup END")

    def _set_keymap(self):
        for key in self.keymap.keys():
            vim.command(f"nnoremap <buffer> {key} :call BufApp_KeyDispatcher(['{self.name}', '{key}'])<cr>")
            
    def _set_syntax(self):
        pass

    def _create_buffer(self):
        self.bufnr = vim.eval(f"bufadd('{self.name}')")
        vim.eval(f"bufload({self.bufnr})")

class BufferSmartPoint:
    def __init__(self):
        self.buf = None

    def create(self, buf):
        self.buf = buf
        self.buf.create()

    def get(self):
        return self.buf

class Layout: 
    def __init__(self, active_win=None):
        self.active_win_name = active_win
        self.windows = {} # str -> winids
        self.buffers = {} # str -> Buffer

    def _create_windows(self):
        raise RuntimeError("dont implemented.")

    def _close_windows(self):
        for key, val in self.windows.items():
            with CurrentWindowGuard(val):
                vim.command("q")

    def create(self, buf_dict=None): 
        with CurrentWindowGuard(): 
            self.windows = self._create_windows()
        if self.active_win_name:
            winid = self._jump_to_winid(self.windows[self.active_win_name])
        if buf_dict: 
            self.reset_buffers(buf_dict)
        return self.windows

    def get_windows(self):
        return self.windows

    def set_buffer(self, name, buf):
        """ remove the original buffers
        """
        wid = self.windows[name]
        with CurrentWindowGuard(wid):
            vim.command(f"b {buf.bufnr}")
            if self.buffers.get(name) is not None: 
                self.buffers.get(name).delete()
        self.buffers[name] = buf
    
    def reset_buffers(self, buf_dict): 
        """ set buffer while create.
        """
        for key in buf_dict.keys():
            self.set_buffer(key, buf_dict[key])

    def _jump_to_winid(self, winid):
        vim.eval(f"win_gotoid({winid})")

    def _get_current_winid(self):
        return vim.eval("win_getid()")

    def windiff(self, names, on=True):
        for name in names: 
            with CurrentWindowGuard(self.windows[name]): 
                if on: vim.command("diffthis")
                else: vim.command("diffoff")

class TabeLayout(Layout):
    """
    create window in a new tabe page 
    """
    def _create_windows(self):
        vim.command("tabe")
        ret = {"win": self._get_current_winid()}
        return ret

class Application: 
    def __init__(self):
        pass

    def start(self):
        pass

class FixStringBuffer(Buffer):
    def __init__(self, text, history=None, options=None):
        super().__init__("fix_string", history, options)
        self.text = text

    def onredraw(self):
        self._clear()
        self._put_string(self.text)

class BashCommandResultBuffer(Buffer):
    def __init__(self, bash_cmd, syntax=None, history=None, options=None):
        super().__init__("bash_cmd", history, options)
        self.syntax = syntax
        self.bash_cmd = bash_cmd

    def oninit(self):
        if self.syntax: 
            vim.command(f'set syntax={self.syntax}')

    def onredraw(self):
        self._clear()
        if self.bash_cmd: 
            vim.command(f"silent! 0read! {self.bash_cmd}")
        vim.command(f"normal! gg")

class HelloworldApp(Application):
    def __init__(self):
        super().__init__()
        self.layout = TabeLayout(active_win="win")
        self.mainbuf = FixStringBuffer("Hellow World")

    def start(self):
        self.layout.create()
        self.mainbuf.create()
        self.layout.set_buffer("win", self.mainbuf)

@vim_register(command="TT")
def HelloworldTest(args):
    app = HelloworldApp()
    app.start()
