import vim
import traceback
from .vim_utils import *
from .func_register import vim_register
import time
import threading
from .multiprocess_utils import ProductConsumerModel, CancellableWorker
import subprocess
from .sema_utils import SemaPool
from functools import partial
from . import remote_fs
import os
from .rpc import rpc_wait, rpc_call
from .buf_app import FixStringBuffer
from .command_doc_popup import DocPreviewBuffer

class USEWindowCallback:# {{{
    def on_update(self):
        pass
        
    def on_create(self):
        pass

    def on_done(self):
        pass

    def on_destory(self):
        pass

    def is_alive(self):
        pass
# }}}

# wrapper for the vim popup windows
class Window:# {{{
    def __init__(self):
        self.wid = -1
        self.hidden = False
        self.buf = None
        pass

    def is_create(self):
        return self.wid != -1

    def create(self):
        self.hidden = True
        pass

    def destory(self):
        self.assert_create()
        vimeval("popup_close(%s)" % self)
        self.wid = -1
        self.buf = None
        self.hidden = False

    def hide(self):
        self.assert_create()
        self.hidden = True
        vimeval("popup_hide(%s)" % self)

    def show(self):
        self.assert_create()
        self.hidden = False
        vimeval("popup_show(%s)" % self)

    def resize(self):
        pass

    def redraw(self):
        pass

    def assert_create(self):
        assert self.is_create(), "please create first."

    def _execute_normal(self, cmd):
        self.assert_create()
        vim_cmd = VimVariable().assign(cmd)
        vimeval("win_execute(%s, 'silent normal! '.%s)" % (self, vim_cmd))
        vim_cmd.delete()

    def _execute(self, cmd):
        self.assert_create()
        vim_cmd = VimVariable().assign(cmd)
        vimeval("win_execute(%s, %s)" % (self, vim_cmd))
        vim_cmd.delete()

    def vim_eval(self, expr):
        self._execute('let tmp=%s' % expr)
        return vimeval("tmp")

    def gotoline(self, line):
        assert isinstance(line, int)
        self._execute_normal("%sGzz" % line)

    def __str__(self):
        return str(self.wid)

    def up_page(self):  
        pass

    def down_page(self):  
        pass# }}}

class PreviewWindow(Window):# {{{
    class ShowableItem:
        def getBuffer(self):
            raise NotImplementedError()
        def getTitle(self):
            raise NotImplementedError()
        def getWinOptions(self):
            return {}
        def getLineNumber(self):
            raise NotImplementedError()
        #def __del__(self):
            #bufnr = self.getBuffer()
            #vim.eval("bwipeout")

    class LocationItem(ShowableItem):
        def __init__(self, loc):
            self.loc = loc
        def getBuffer(self):
            filename = self.loc.getfile()
            return remote_fs.FileSystem().bufload_file(filename)
        def getTitle(self):
            return self.loc.getfile()
        def getLineNumber(self):
            return self.loc.getline()

    class ContentItem(ShowableItem):
        def __init__(self, title, content, syntax, line, options={}):
            self.syntax = syntax
            self.content = content
            self.title = title
            self.line = line
            self.options = options
            self.buffer = FixStringBuffer(self.content, self.syntax)
            self.buffer.create()
        def getBuffer(self):
            return self.buffer.bufnr
        def getTitle(self):
            return self.title
        def getLineNumber(self):
            return self.line
        def getWinOptions(self):
            return self.options

    def __init__(self, showable: ShowableItem, **args):
        super().__init__()
        self.showable = showable
        if "title" not in args:
            args['title'] = showable.getTitle()
        self.options = {
            "maxheight": 17, 
            "minheight": 17, 
            "line": 'cursor+5',
            "pos": "topleft", 
            "border": [], 
            "title": args['title'],
            "minwidth": 100, 
            "maxwidth": 100, 
            "posinvert": False,
        }
        if GetCursorScreenXY()[0] > 17 + 5 + 2:
            self.options.update({
                "line": "cursor-5", 
                "pos": "botleft"
            })
        self.options.update(showable.getWinOptions())
        self.options.update(args) 
    
    def create(self):
        super().create()
        from .clangd_client import StopAutoCompileGuard
        with StopAutoCompileGuard():
            opt = VimVariable().assign(self.options)
            self.buf = self.showable.getBuffer()
            self.wid = int(vimeval("popup_create(%s, %s)"% (self.buf, opt)))
            vimeval(f"setbufvar({self.buf}, 'bufhidden', 'wipe')")
            for setting in ['cursorline', 'number', 'relativenumber']:
                self._execute('silent setlocal ' + setting)
            self.gotoline(self.showable.getLineNumber())
            if 'search' in self.options: 
                self._execute("match Search /%s/" % self.options['search'])
# }}}

"""
Location Preview Windows: 
"""
class BoxListWindowManager:# {{{
    manager = None
    def __init__(self):
        self.wins = {}
        
    @staticmethod
    def singleton():
        if BoxListWindowManager.manager is None:
            BoxListWindowManager.manager = BoxListWindowManager()
        return BoxListWindowManager.manager

    def insert(self, win):
        self.wins[win.wid] = win

    def delete(self, win):
        del self.wins[win.wid]

    @staticmethod
    def on_key(winid, key):
        self = BoxListWindowManager.singleton()
        if winid not in self.wins: # means the  window is already deleted, ignore the key.
            return False
        ret = self.wins[winid].on_key(key)
        log(f"get key: {key}, processed: {ret}")
        return ret

    @staticmethod
    def on_close(winid, code):
        self = BoxListWindowManager.singleton()
        if winid not in self.wins: # means the  window is already deleted, ignore the key.
            return False
        return self.wins[winid].on_close(code)
# }}}

class BoxListItem:# {{{
    def __init__(self):
        self.loc = remote_fs.Location()
        self.column = []

    @staticmethod
    def from_search_result(search):
        """
        "   item have keys : 
        "       filename : the filename 
        "       lnum     : the line number
        "       text     : the text of results. one line
        "       cmd      : cmd to jump to the file and lines
        "       source   : where is the data from. which searcher.
        "       other    : where is the data from. which searcher.
        """
        return search
# }}}

class BoxListWindow(Window):# {{{
    def __init__(self, items, inp=None, title="UniverseSearch(@xiongkun):", keymap={}, callback={}, **args):
        super().__init__()
        self.items = items
        from threading import Lock
        self.win_options = {
            "border": [], 
            "h": 20, 
            "title": title, 
            "syntax": "search",
            "maxheight": 40, 
            "maxwidth": 200,
            "cursorline": True,
            "highlight": "Normal",
            "borderhighlight": ["Grep"],
            'mapping': False,  
        }
        """
        mapping = False is important, see 'h popup_create-arguments' for more details.
        """
        self.callback = callback
        self.keymap = keymap
        self.options = args
        self.cur = 1 # the position of the cursor: line number
        self.base = 1
        self.last_search = inp
        self.create()
        self._set_line(1)

    def set_content(self, title):
        self._execute("%d")  # clear
        self._execute(vim_format('call setbufline(winbufnr(%s), 1, "%s")', str(self), title))
    
    def _set_options(self, key, val):
        cmd = ('call popup_setoptions(%s, {"%s":%s})'%
            (str(self), key, val))
        #log(cmd)
        self._execute(cmd)

    def set_border_color(self, hl_group):
        self._set_options("borderhighlight", '["%s"]' % hl_group)

    def set_title(self, title):
        self._set_options("title", title)

    def goto(self, item, method):
        if item['filename'] == "": return 
        loc = remote_fs.Location(item['filename'])
        remote_fs.GoToLocation(loc, method)
        vimcommand(item['cmd'])

    @staticmethod
    def _parse(items):
        tmp = []
        for idx, item in enumerate(items):
            l = [
                str(idx+1), 
                item['source'], 
                item.get("other", "").strip(), 
                vimeval('FilenameTrimer("%s")' % item['filename']),
                vimeval(vim_format('TextTrimer("%s")', item['text'].strip())),
            ]
            tmp.append(l)
        return print_table(tmp)

    def _create_window(self):
        opts = VimVariable().assign(self.win_options)
        wid = int(vimeval("popup_create('Loading', %s)" % opts))
        return wid

    def create(self):
        super().create()
        from .clangd_client import StopAutoCompileGuard
        with StopAutoCompileGuard():
            self.wid = self._create_window()
            BoxListWindowManager.singleton().insert(self)
            if len(self.items): self.update(self.items)
            vimeval("SetWindowsCallBack(%s)" % self)
            syntax = self.win_options.get("syntax", "") 
            if syntax:
                self._execute('set ft=%s' % syntax)

    def update(self, items):
        """ 
        [thread unsafty, please do this in UIThread.]:
        update items into the end of the windows.
        for window dynamic update.
        """
        if not self.is_create(): # means the windows already deleted by other thread. so just do nothing.
            return False
        self.items = items
        if len(self.items) == 0: 
            self.set_content("Empty.")

        if len(self.items) > 0: 
            content = self._parse(self.items)
            vim_con = VimVariable().assign(content)
            self._execute("%d")  # clear
            self._execute('call setbufline(winbufnr(%s), "$", %s)' % (self, vim_con))
            self._set_line(self.cur)
            vim_con.delete()
        return True

    def on_close(self, code):
        """ when user close this win.
        """
        if 'on_close' in self.callback: self.callback['on_close'](self)
        BoxListWindowManager.singleton().delete(self)
        self.destory()

    def _set_line(self, idx):
        """ return false for failed.
        """
        if idx <= 0 : idx = 1
        if idx > len(self.items): idx = len(self.items)
        self.cur = idx
        self._execute("normal! %dG" % self.cur)
        return self.cur

    def cursor_move(self, key):
        offset = {
            'j': 1, 
            'k': -1,
            'h': -10, 
            'l': 10,
            'G': 100000,
            'g': -100000,
            "<up>": -1, 
            "<down>": 1,
        }
        self._set_line(self.cur + offset[key])
    
    def _search_start(self, key):   
        text = self._getinput(key)
        if text == '' or text == "":
            return 
        self._execute("match Search /%s/" % text)
        self.last_search = text
        self._search(text, key)
    
    def _search(self, text, direct):
        self._execute('silent! ' + direct + text) # ignore the Pattern Not Found exception.
        self._sync_cur()

    def _search_jump(self, key):
        if self.last_search is None: 
            return
        mmap = {"n": "/", "N": "?"}
        self._search(self.last_search, mmap[key])

    def _sync_cur(self):
        win_cur = int(self.vim_eval("line('.')"))
        self._set_line(win_cur)

    @staticmethod
    def _getinput(prompt):
        return vimeval("quickui#core#input('%s', '')" % prompt)

    def _getcuritem(self):
        base = 1
        if self.cur - base < len(self.items) and self.cur - base >= 0: 
            return self.items[self.cur - base]
        return None

    def moveto_preview_window(self):
        locs = items2locs(self.items)
        base = 1
        GPW.set_locs(locs, self.cur - base)
        GPW.show()

    def on_default_key(self, key):
        """ when user type key board. 
            return true: if processed.
            return false: to call default process function. (VimScript)
        """
        if key == '<m-1>': 
            return True

        key2jump = {# {{{
            '<cr>': 'e',
            's': 's',
            'v': 'v',
            't': 't', 
        }# }}}
        def close_boxlist(jump_method):# {{{
            wid = self.wid
            vimeval("popup_close(%d)" % wid)
            if jump_method in key2jump: 
                vimcommand("let g:default_jump_cmd = '%s'" % key2jump[jump_method])
                if self._getcuritem():
                    self.goto(self._getcuritem(), key2jump[jump_method])# }}}
            
        if key in ['j', 'k', 'h', 'l', 'G', 'g', '<up>', '<down>']:
            self.cursor_move(key)
            return True

        if key in key2jump :
            close_boxlist(key)
            return True

        if key in ['/', '?']: 
            self._search_start(key)# {{{
            return True# }}}
        if key in ['p']: 
            """ # {{{
            preview mode, move all the location in the PreviewWindow.
            very convienent in edit mode
            """
            self.moveto_preview_window()
            close_boxlist("") # don't jump
            return True# }}}
        if key in ['n', 'N']:
            self._search_jump(key)# {{{
            return True# }}}
        if key in ['f', 'F']: 
            text = self._getinput("filter>%s>" % key)# {{{
            if text not in ["", ""]: 
                def name_filter(item):
                    if text in item['filename']: return True
                    return False
                def inv_name_filter(item):
                    if text in item['filename']: return False
                    return True
                def context_filter(item):
                    assert text.startswith("+")
                    actual_text = text[1:]
                    context = "".join(peek_line(item['filename'], int(item['lnum']), int(item['lnum'])+5))
                    item['text'] = context
                    if actual_text  in context: return True
                    return False
                m = {'f': name_filter, 'F': inv_name_filter}
                if text.startswith('+'): 
                    if remote_fs.FileSystem().is_remote(): 
                        print ("In remote mode, search context is not unsupported now.")
                        return True
                    filter_fn = context_filter
                else: filter_fn = m[key]
                self.items = list(filter(filter_fn, self.items))
                self.update(self.items)
            return True# }}}
        if key in ['d', 'D']: 
            search_text = remove_angle_bracket(self.last_search)
            if key == 'd': 
                search_text = None
            def on_return(items):
                self.update(items)
            items = rpc_call("grepfinder.sema_filter", on_return, self.items, search_text)
            return True# }}}
        if key in ['I']: 
            if remote_fs.FileSystem().is_remote(): 
                print ("In remote mode, quickfix list is not unsupported now.")
                return True
            def do_include(filename):# {{{
                log("start include : ", filename)
                IncludePreviewedFile(None, osp.abspath(filename))
            do_include(self._getcuritem()['filename'])
            self.moveto_preview_window()
            close_boxlist("")
            return True# }}}
        if key in ['q']: 
            if remote_fs.FileSystem().is_remote(): 
                print ("In remote mode, quickfix list is not unsupported now.")
                return True
            locs = items2locs(self.items)# {{{
            close_boxlist("") # don't jump
            SetQuickFixList(locs)
            return True# }}}

        return False

    def on_key(self, key):
        self.on_default_key(key)
        return True # consume all char and prevent modify the main buffer
    
    @classmethod
    def GetWindowCallback(cls):
        class Callback(USEWindowCallback):
            def on_update(self, items):
                if len(items): self.empty = False
                self.length = len(items)
                self.win.set_title('"Total Results: [%d]"' % self.length)
                self.win.update(items)
                
            def on_create(self, inp, items, **opts):
                self.win = cls(items, inp=inp, **opts)
                self.empty = True
                if len(items): self.empty = False

            def on_done(self):
                self.win.set_border_color("Filename")
                if self.empty and self.win:
                    self.win.set_content("Not Found.")

            def on_destory(self):
                pass

            def is_alive(self):
                return self.win.is_create()

        return Callback()
# }}}

class LocationPreviewWindows:# {{{
    def __init__(self):
        self.pwin = None
        self.hidden = True
        self.candidate_locs = []
        self.candidate_idx = 0
        self.win_ops = {}
        self.last_find_cursor = (-1, -1)

    def cur_loc(self):
        if self.candidate_idx < 0: return 
        if self.candidate_idx >= len(self.candidate_locs): return 
        return self.candidate_locs[self.candidate_idx]
    
    def go(self):
        loc = self.cur_loc()
        if self.pwin is not None:
            self.pwin.destory()
            self.pwin = None
        if loc is None : return 
        if len(self.candidate_locs) == 1: 
            self.win_ops['title'] = loc.getTitle()
        else: 
            self.win_ops['title'] = f"[{self.candidate_idx+1} / {len(self.candidate_locs)}] " + loc.getTitle()
        self.pwin = PreviewWindow(loc, **self.win_ops)
        self.pwin.create()
        if self.hidden: self.pwin.hide()

    def set_locs(self, locs, idx=0, **args):
        shows = [ PreviewWindow.LocationItem(loc) for loc in locs ]
        self.set_showable(shows, idx)

    def set_showable(self, showable, idx=0, **args):
        self.candidate_locs = showable
        self.win_ops = args
        self.candidate_idx = idx
        self.go()

    def page_down(self):
        if self.pwin is not None:
            self.pwin._execute_normal("")
            self.pwin._execute_normal("zz")

    def page_up(self):
        if self.pwin is not None:
            self.pwin._execute_normal("")
            self.pwin._execute_normal("zz")

    def next(self):
        if self.candidate_idx < len(self.candidate_locs) - 1:
            self.candidate_idx += 1
        self.show()
        self.go()

    def prev(self):
        if self.candidate_idx > 0:
            self.candidate_idx -= 1
        self.show()
        self.go()

    def show(self):
        self.hidden = False
        if self.pwin is not None:
            self.pwin.show()

    def hide(self):
        self.hidden = True
        if self.pwin is not None:
            self.pwin.hide()

    def trigger(self):
        if self.hidden: self.show()
        else: self.hide()

    def find(self, word=None):
        new_xy = GetCursorXY()
        if new_xy == self.last_find_cursor:
            self.trigger()
        else: 
            self.last_find_cursor = new_xy
            if not word: word = vimeval("expand('<cword>')")
            if not word: return 
            pwd = GetPwd()
            USEngineOpts = {
                'searchers': [LSPSearcher, CtagSearcher, GrepSearcher], 
                'async_mask': [0, 0, 1],
                'window': self.GetWindowCallback(),
            }
            self.use = UniverseSearchEngine(USEngineOpts)
            self.use.search(word, pwd)
            self.use.render()
    
    def open_in_preview_window(self):
        loc = self.cur_loc()
        if  loc is not None and isinstance(loc, PreviewWindow.LocationItem):
            loc = loc.loc
            remote_fs.GoToLocation(loc, ".") 
        else: 
            print("Please set locations of preview windows.")
        self.hide()

    def GetWindowCallback(this):
        class Callback(USEWindowCallback):
            def on_update(self, items):
                locs = items2locs(items)
                self.empty = (len(locs) == 0)
                this.set_locs(locs, idx=0, search=self.inp)
            def on_create(self, inp, items, **opts):
                self.inp = inp
                locs = items2locs(items)
                self.empty = (len(locs) == 0)
                this.set_locs(locs, idx=0, search=self.inp)
                this.show()
            def on_done(self):
                pass
            def on_destory(self):
                this.hide()
            def is_alive(self):
                return not this.hidden
        return Callback()


@Singleton
class GlobalPreviewWindowHandle:
    """ normal mode:
        <M-p> will trigger IFind. 
        if you move the mouse: <M-p> will refind. 
        if you don't move the mouse and <M-p> again, you will close preview window.
    """
    def __init__(self):
        self.stack = []
        self.stack.append(({}, LocationPreviewWindows()))

    def __getattr__(self, key):
        assert len(self.stack) > 0
        hooker = self.stack[-1][0].get(key, None)
        target = getattr(self.stack[-1][1], key)
        if hooker: hooker(self)
        return target

    def register_hooker(self, key, fn):
        self.stack[-1][0][key] = fn
    
    def push_window(self): 
        self.hide()
        self.stack.append(({}, LocationPreviewWindows()))
    
    def pop_window(self):
        self.stack.pop()

    def tmp_window(self):
        self.push_window()
        def hide_hook(self):
            self.stack.pop()
        self.register_hooker("hide", hide_hook)
        

GlobalPreviewWindow = GlobalPreviewWindowHandle()
GPW = GlobalPreviewWindowHandle()
# }}}

# ==============

class Searcher:# {{{
    def __init__(self, opts):
        pass

    def do_search(self, inp, d):
        return []

    def get_workers(self, inp, d):
        def wrapper(qid):
            return self.do_search(inp, d)
        return CancellableWorker(wrapper)
    
    def loc2searchitem(self, loc):
        lnum = loc.getline() + 1 # 0-base to 1-base
        d = dict(
            filename = loc.getfile(), 
            lnum = lnum,
            cmd = "" + str(lnum),
            text = GetTextFromLocation(loc))
        return d

    def force_cancel(self, inp, d):
        pass
# }}}
@Singleton
class MessageWindow:
    def __init__(self):
        self.doc_buffer = DocPreviewBuffer()
        self.markdowns = []
        self.cur = 0
        self.is_show = False

    def hide(self):
        self.doc_buffer.hide()
        self.is_show = False

    def show(self):
        if self.cur < len(self.markdowns) and self.cur >= 0:
            self.doc_buffer.set_markdown_doc(self.markdowns[self.cur])
            self.doc_buffer.show()
            self.is_show = True

    def set_markdowns(self, markdowns):
        self.markdowns = markdowns
        if self.is_show: self.show()


class LSPSearcher(Searcher):# {{{
    def do_search(self, inp, d):
        try:
            old_buf_pos = int(vim.eval("bufnr()"))
            old_cur_pos = GetCursorXY()
            with CursorGuard():
                with CurrentBufferGuard(): 
                    vim.command('call CocAction("jumpDefinition")')
                    buf_pos = int(vim.eval("bufnr()"))
                    cur_pos = GetCursorXY()
            #log("[LSPSearcher]", old_buf_pos, old_cur_pos, buf_pos, cur_pos)
            if buf_pos == old_buf_pos and old_cur_pos == cur_pos: 
                return []
            item = self.loc2searchitem(remote_fs.Location(buf_pos, cur_pos[0], cur_pos[1], base=1).to_base(0))
            item['source'] = 'LSP'
            #log("[LSPSearcher]", item)
            return [item]
        except Exception as e:
            log(f"[LSPSearcher] Exception: {e}")
            return []

class CtagSearcher(Searcher):# {{{
    def do_search(self, inp, d):
        # TODO move to python implement
        return vimeval("CtagSearcher('%s')" % inp)# }}}

class CtrlPSearcher(Searcher):# {{{
    def do_search(self, inp, d):
        return []# }}}

class GrepSearcher(Searcher):# {{{
    def get_workers(self, inp, d):
        class GrepSearchWorker(CancellableWorker):
            def __init__(self):
                super().__init__(None)
            def __call__(self, qid):
                from .rpc import rpc_server
                self.stream = rpc_server().call_stream(
                    "grepfinder.search", self.process, 
                    self.finish, d, inp
                )

            def cancel(self):
                self.force_cancel()
                self.child = None
                self.stream.delete()

            def force_cancel(self):
                if self.child.poll() is None: 
                    self.child.terminate()

            def set_callback(self, finish, process):
                self.finish = finish
                self.process = process


        return GrepSearchWorker()
# }}}

class ClangdIndexSearcher(Searcher):# {{{
    #TODO
    """ clangd searcher: 
        1. clangd GoToDefinition
        2. clangd Indexer Search
    """
    def do_search(self, inp, d):
        inp = remove_angle_bracket(inp)
        from .indexer import FindIndexer, filter_exactly
        locs = FindIndexer([inp], filter_exactly, silent=True)
        if locs is None: 
            return []
        rets = [self.loc2searchitem(l) for l in locs]
        for r in rets:
            r['source'] = "Idx"
        return rets# }}}

def items2locs(items):# {{{
    ret = []
    for item in items:
        if item.get('lnum', "") == "": continue
        ret.append(remote_fs.Location(
            item['filename'],
            int(item['lnum']),
            int(item.get('col', 1))))
    return ret# }}}

def remove_angle_bracket(inp):# {{{
    inp = inp.replace("\\<", "")
    inp = inp.replace("\\>", "")
    return inp# }}}

def filter_by_definition(search_text, items):
    def definition_filter(item):
        l = items2locs([item])[0]
        return SemaPool.get_sema(l.getfile()).is_function_definition(l, search_text)
    items = list(filter(definition_filter, items))
    return items

USEngine = None

class UniverseSearchEngine(Searcher):# {{{
    def __init__(self, opts):
        self.opts = opts
        self.pcm = None
        from threading import Lock
        self.last_results = []
        self.sync = []
        self.async_ = []
        self.all = []
        self.query_id = 0 # indicate the current query id.
        for s_cls, is_async in zip(self.opts['searchers'], self.opts['async_mask']):
            s = s_cls(opts)
            if not is_async: self.sync.append(s)
            else :           self.async_.append(s)
            self.all.append(s)
        self.window = self.opts.get('window', None)

    def update(self, qid, items):
        # modify the data.
        log("update with : ", qid, "  with len(items) == ", len(items) if items else 0, "  Current qid:", self.query_id)
        if qid == self.query_id and items is not None and len(items) > 0:
            self.last_results = self.last_results + items
            self.last_results = self.post_process(self.last_results)
            # update the window
            log("on update: ", self.window.is_alive(), " with query_id: ", qid)
            if self.window is not None and self.window.is_alive(): 
                self.window.on_update(self.last_results)

    def on_worker_done(self, qid):
        if qid == self.query_id and self.window is not None and self.window.is_alive(): 
            log("worker_done accept : ", qid)
            self.window.on_done()

    def render(self):
        box_items = [ BoxListItem.from_search_result(r) for r in self.last_results ]
        def onclose(window):
            self.kill_async()
        self.window.on_create(self.last_input, box_items, callback={"on_close": onclose})
        if len(self.async_) == 0: 
            self.window.on_done()

    def clear_history(self):
        self.last_input = ""
        self.last_results = []
        self.query_id += 1

    def kill_async(self):
        if self.pcm is not None:
            self.pcm.destory()
            for s in self.workers: 
                s.cancel()
            self.workers = None
            self.pcm = None

    def start_async(self, workers):
        # Refactor by xiongkun in 2023-5-27
        # 1. make all the aysnc logic into RPC
        # 2. add rpc stream mode.
        if len(workers) == 0 : return 
        qid = self.query_id
        def update_wrapper(items):
            self.update(qid, items)

        def done_callback(results):
            self.update(qid, results)
            self.on_worker_done(qid)
            self.kill_async()

        self.workers = workers
        assert len(self.workers) <= 1 
        for worker in self.workers: 
            worker.set_callback(done_callback, update_wrapper)
            worker.on_finish = done_callback
            worker.on_process = update_wrapper
            worker(qid)

    def search(self, inp, directory, mask=None):
        if remote_fs.FileSystem().is_remote():
            directory = remote_fs.FileSystem().cwd
        if inp is None or inp == "" :
            return self.last_results
        with NotChangeQuickfixGuard():
            self.clear_history()
            self.last_input = inp
            #vimeval("CreateAndImportTmpTags()")
            # [search]
            results = []
            workers = []
            if not mask: 
                mask = [True] * len(self.all) 
            else: 
                assert len(mask) == len(self.all)
            for m, s in zip(mask, self.all):
                if not m: continue
                w = s.get_workers(inp, directory)
                if not isinstance(w, list): w = [w]
                if id(s) in map(id, self.sync): 
                    for single_worker in w:
                        results = results + single_worker(self.query_id)
                if id(s) in map(id, self.async_): 
                    workers = workers + w
            self.start_async(workers)
            # [modity the results.]
            result = self.post_process(results)
            self.last_results = results
        return results

    def post_process(self, results):
        # [sort]
        results = self.sort(results)
        # [unique]
        results = self.unique(results)
        # [filter], you can filter in the f/F command in BoxListWindow
        # results = self.filter(results)
        return results

    def sort(self, results):
        def get_list_by_name(rs, name):
            return [ r for r in rs if r['source'] == name ]
        return (
            get_list_by_name(results, "LSP") + 
            get_list_by_name(results, "Idx") + 
            get_list_by_name(results, "User") + 
            get_list_by_name(results, "CTag") + 
            get_list_by_name(results, "Grep")
        )

    def filter(self, results):  
        if len(results) == 0: return 
        res_vim = VimVariable(value=results)
        results = vimeval("ResultsFilter(%s)" % res_vim)
        res_vim.delete()
        return results

    def unique(self, results):
        import os.path as osp
        def sig(r):
            return (osp.abspath(r['filename']), r['cmd'])
        return Unique(results, sig)
        
    @staticmethod
    def singleton():
        global USEngine
        USEngineOpts = {
            'searchers': [LSPSearcher, CtagSearcher, CtrlPSearcher, GrepSearcher], 
            'async_mask': [0, 0, 0, 1],
        }
        USEngineOpts["window"] = BoxListWindow.GetWindowCallback()
        if USEngine is None: 
             USEngine = UniverseSearchEngine(USEngineOpts)
        return USEngine# }}}

@vim_register(with_args=True, command_completer="file", command="ChangeSearchDirectory")
def ChangeSearchGlobal(args): 
    assert len(args) <= 1
    directory = vim.eval("getcwd()")
    if len(args) == 1:
        directory = args[0]
    log("Director:", directory)
    directory = vim.eval(f'expand("{directory}")')
    vim.command(f'let g:nerd_search_path="{directory}"')

#======  unit test of search and windows.

def test():# {{{
    USE = UniverseSearchEngine.singleton()
    USE.search("InterpreterCore")
    USE.render()

def test1():
    win = PreviewWindow(
        PreviewWindow.LocationItem(remote_fs.Location("/home/data/web/scripts/test_unsqueeze.py", 20, 1)
    ))
    win.create()
    win.show()
    time.sleep (1)
    win.hide()
    time.sleep (1)
    win.show()
    time.sleep (1)
    win.destory()

def test2():
    GlobalPreviewWindow.set_locs(
        [remote_fs.Location("/home/data/web/scripts/test_unsqueeze.py", 10, 1), 
        remote_fs.Location("/home/data/web/scripts/test_unsqueeze.py", 4, 1), 
        remote_fs.Location("/home/data/web/scripts/test_unsqueeze.py", 8, 1)]
    )
    GlobalPreviewWindow.show()

def test_grep():
    grep = GrepSearcher({})
    grep.do_search("Interpreter", "/home/data/Paddle/")

def test3():
    GlobalPreviewWindow.set_showable([
        PreviewWindow.ContentItem("Custom", ["## sdfsdf"], "markdown", 1),
        PreviewWindow.ContentItem("ssss", ["xiongkun", "good"], "markdown", 1)
    ])
    GlobalPreviewWindow.show()
# }}}
