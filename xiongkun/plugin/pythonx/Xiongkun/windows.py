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
import os

class Buffer:# {{{
    def __init__(self, name):
        self.bufid = -1
        self.name = name

    def load(self, file=None):
        if file: self.name = file
        self.bufid = int(vimeval("bufadd('%s')"% self.name))
        vimeval("bufload(%s)" % self.bufid)
        return self

    def __str__(self):
        return str(self.bufid)# }}}

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
    def __init__(self, loc, **args):
        super().__init__()
        self.loc = loc
        self.options = {
            "maxheight": 17, 
            "minheight": 17, 
            "line": 'cursor+5',
            "pos": "topleft", 
            "border": [], 
            "title": loc.getfile(),
            "minwidth": 100, 
            "maxwidth": 100, 
            "posinvert": False,
        }
        if GetCursorScreenXY()[0] > 17 + 5 + 2:
            self.options.update({
                "line": "cursor-5", 
                "pos": "botleft"
            })
        self.options.update(args) 
    
    def create(self):
        super().create()
        from .clangd_client import StopAutoCompileGuard
        with StopAutoCompileGuard():
            opt = VimVariable().assign(self.options)
            self.buf = Buffer(self.loc.getfile()).load()
            self.wid = int(vimeval("popup_create(%s, %s)"% (self.buf, opt)))
            for setting in ['cursorline', 'number', 'relativenumber']:
                self._execute('silent setlocal ' + setting)
            self.gotoline(self.loc.getline())
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
        self.loc = Location()
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
        loc = Location(item['filename'])
        GoToLocation(loc, method)
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
                if text.startswith('+'): filter_fn = context_filter
                else: filter_fn = m[key]
                self.items = list(filter(filter_fn, self.items))
                self.update(self.items)
            return True# }}}
        if key in ['d', 'D']: 
            search_text = remove_angle_bracket(self.last_search)
            if key == 'd': 
                search_text = None
            items = filter_by_definition(search_text, self.items)
            self.update(items)
            return True# }}}
        if key in ['I']: 
            def do_include(filename):# {{{
                log("start include : ", filename)
                IncludePreviewedFile(None, osp.abspath(filename))
            do_include(self._getcuritem()['filename'])
            self.moveto_preview_window()
            close_boxlist("")
            return True# }}}
        if key in ['q']: 
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

class GlobalPreviewWindow:# {{{
    pwin = None
    hidden = True
    candidate_locs = []
    candidate_idx = 0
    win_ops = {}

    @staticmethod
    def cur_loc():
        if GPW.candidate_idx < 0: return 
        if GPW.candidate_idx >= len(GPW.candidate_locs): return 
        return GPW.candidate_locs[GPW.candidate_idx]
    
    @staticmethod
    def go():
        loc = GPW.cur_loc()
        if GPW.pwin is not None:
            GPW.pwin.destory()
            GPW.pwin = None
        if loc is None : return 
        GPW.win_ops['title'] = "[%d / %d]"%(GPW.candidate_idx+1, len(GPW.candidate_locs)) + loc.getfile()
        GPW.pwin = PreviewWindow(loc, **GPW.win_ops)
        GPW.pwin.create()
        if GPW.hidden: GPW.pwin.hide()

    @staticmethod
    def set_locs(locs, idx=0, **args):
        GPW.candidate_locs = locs
        GPW.win_ops = args
        GPW.candidate_idx = idx
        GPW.go()

    @staticmethod
    def page_down():
        if GPW.pwin is not None:
            GPW.pwin._execute_normal("")
            GPW.pwin._execute_normal("zz")

    @staticmethod
    def page_up():
        if GPW.pwin is not None:
            GPW.pwin._execute_normal("")
            GPW.pwin._execute_normal("zz")

    @staticmethod
    def next():
        if GPW.candidate_idx < len(GPW.candidate_locs) - 1:
            GPW.candidate_idx += 1
        GPW.show()
        GPW.go()

    @staticmethod
    def prev():
        if GPW.candidate_idx > 0:
            GPW.candidate_idx -= 1
        GPW.show()
        GPW.go()

    @staticmethod
    def show():
        GPW.hidden = False
        if GPW.pwin is not None:
            GPW.pwin.show()

    @staticmethod
    def hide():
        GPW.hidden = True
        if GPW.pwin is not None:
            GPW.pwin.hide()

    @staticmethod
    def trigger():
        if GPW.hidden: GPW.show()
        else: GPW.hide()


    """ normal mode:
        <M-p> will trigger IFind. 
        if you move the mouse: <M-p> will refind. 
        if you don't move the mouse and <M-p> again, you will close preview window.
    """
    last_find_cursor = (-1, -1)
    @staticmethod
    def find(word=None):
        new_xy = GetCursorXY()
        if new_xy == GPW.last_find_cursor:
            GPW.trigger()
        else: 
            GPW.last_find_cursor = new_xy
            if not word: word = vimeval("expand('<cword>')")
            if not word: return 
            pwd = GetPwd()
            USEngineOpts = {
                'searchers': [LSPSearcher, CtagSearcher, GrepSearcher], 
                'async_mask': [0, 0, 1],
                'window': GPW.GetWindowCallback(),
            }
            GPW.use = UniverseSearchEngine(USEngineOpts)
            GPW.use.search(word, pwd)
            GPW.use.render()
    
    @staticmethod
    def open_in_preview_window():
        if GPW.cur_loc() is not None: 
            GoToLocation(GPW.cur_loc(), "p") 
        else: 
            print("Please set locations of preview windows.")
        GPW.hide()

    @classmethod
    def GetWindowCallback(cls):
        class Callback(USEWindowCallback):
            def on_update(self, items):
                locs = items2locs(items)
                self.empty = (len(locs) == 0)
                GPW.set_locs(locs, idx=0, search=self.inp)
                
            def on_create(self, inp, items, **opts):
                self.inp = inp
                locs = items2locs(items)
                self.empty = (len(locs) == 0)
                GPW.set_locs(locs, idx=0, search=self.inp)
                GPW.show()

            def on_done(self):
                pass

            def on_destory(self):
                GPW.hide()

            def is_alive(self):
                return not GPW.hidden

        return Callback()
# }}}

GPW = GlobalPreviewWindow
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
            item = self.loc2searchitem(Location(buf_pos, cur_pos[0], cur_pos[1], base=1).to_base(0))
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
            def __init__(self, inp, directory):
                super().__init__(None)
                self.directory = directory
                self.inp = inp
                self.child = None
            def __call__(self, qid):
                return GrepSearcher.do_search(self.inp, self.directory, self) 
            def cancel(self):
                self.force_cancel()
                self.child = None
            def force_cancel(self):
                if self.child.poll() is None: 
                    self.child.terminate()

        import glob 
        files = glob.glob(d + "/*")
        def f(name):
            return not osp.basename(name).startswith(".") and "build" not in osp.basename(name) and "tag" not in osp.basename(name)
        filter(f, files)
        files = [ f for f in files if osp.isdir(f) ]
        workers = []
        for file in files: 
            abspath = osp.abspath(file)
            workers.append(GrepSearchWorker(inp, abspath))

        # insert FILE as file with depth=1 file search
        workers.append(GrepSearchWorker(inp, "FILE:" + d))
        return workers
    
    @staticmethod
    def do_search(inp, directory, worker):
        extra_args = []
        log("do_search")
        search_config_path = directory + "/search_config"
        if osp.isfile(search_config_path):
            with open(search_config_path, "r") as fp :
                lines = fp.readlines()
                lines = [ l.strip() for l in lines ]
                lines = list(filter(lambda x: x and not x.strip().startswith("#"), lines))
                extra_args = lines

        if directory.startswith("FILE:"): 
            directory = directory.split("FILE:")[1].strip()
            sh_cmd = "find %s -maxdepth 1 -type f | xargs egrep -H -I -n %s \"%s\"" % (directory, " ".join(extra_args), escape(inp))
        else: 
            sh_cmd = "egrep -I -H -n %s -r \"%s\" %s" % (" ".join(extra_args), escape(inp), directory)
        worker.child = subprocess.Popen(sh_cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
        results = []
        for idx, line in enumerate(worker.child.stdout.readlines()):
            try:
                line = line.strip()
                filename = line.split(":")[0].strip()
                lnum = line.split(":")[1].strip()
                text = ":".join(line.split(":")[2:])
                result = {}
                result['filename'] = filename.strip()
                assert lnum.isnumeric(), "Not a valid number."
                result['lnum'] = lnum
                result['text'] = text.strip()
                result['cmd']  = "" + lnum
                result['source']  = "Grep"
            except Exception as e:
                continue
            results.append(result)
        return results

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
        ret.append(Location(
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
        log("worker_done with : ", qid)
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
        if len(workers) == 0 : return 
        def update_wrapper(items, qid):
            vim_dispatcher.call(self.update, args=[qid, items])

        def done_callback(qid):
            vim_dispatcher.call(self.on_worker_done, args=[qid])
            self.kill_async()

        self.workers = workers
        self.pcm = ProductConsumerModel(workers, update_wrapper, done_callback)
        self.pcm.start([self.query_id])

    def search(self, inp, directory, mask=None):
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
        Location("/home/data/web/scripts/test_unsqueeze.py", 20, 1)
    )
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
        [Location("/home/data/web/scripts/test_unsqueeze.py", 10, 1), 
        Location("/home/data/web/scripts/test_unsqueeze.py", 4, 1), 
        Location("/home/data/web/scripts/test_unsqueeze.py", 8, 1)]
    )
    GlobalPreviewWindow.show()

def test_grep():
    grep = GrepSearcher({})
    grep.do_search("Interpreter", "/home/data/Paddle/")
# }}}
