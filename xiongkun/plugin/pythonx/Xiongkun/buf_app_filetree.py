import os
from .buf_app import WidgetBufferWithInputs, WidgetList, TextWidget, SimpleInput, WidgetBuffer, BufferHistory
from .func_register import vim_register
from .vim_utils import SetVimRegister, Normal_GI, Singleton, CurrentEditFile, input_no_throw, get_char_no_throw
import vim
from functools import partial
from .log import debug
from .remote_fs import FileSystem
from .windows import MessageWindow

file_tree_history = BufferHistory("file_tree_history")

class CursorLineBuffer(WidgetBuffer):
    def __init__(self, widgets, name, title, history=None, options=None):
        options = {
            'title': title, 
            'maxwidth': 100, 
            'minwidth':  50,
            'minheight': 30,
            'maxheight': 30, 
            'cursorline': 1,
        }
        super().__init__(widgets, name, history, options)

    def show_label(self, cmd):
        from .quick_jump import JumpLines
        JumpLines([self.wid, self.on_jump_label])

    def on_jump_label(self):
        pass

    def on_enter(self):
        raise NotImplementedError()

    def normal(self, str):
        self.execute(f'normal! {str}')

    def normal_no_except(self, str):
        try: 
            self.normal(str)
        except: 
            pass

    def view_in(self, lnum):
        self.execute(f":{lnum+1}")

    def cur_cursor_line(self):
        self.execute("let g:filetree_line_number=getpos('.')")
        return int(vim.eval("g:filetree_line_number")[1]) - 1

    def on_cursor_move(self, char):
        char = {
            'l': '',
            'h': '', 
            'j': 'j' ,
            'k': 'k' ,
        }[char]
        self.normal(char)
        self.post_cursor_move(char)

    def post_cursor_move(self, char): 
        pass

    def on_key(self, key):
        if super().on_key(key):
            return True
        if key in ['j', 'k', 'l', 'h']: 
            self.on_cursor_move(key)
            return True
        if key in ['<cr>']: 
            self.on_enter()
            return True
        if key in ['<tab>', 'g']: 
            self.show_label(key)
            return True
        if key in ['/']: 
            search = input_no_throw("/")
            self.last_search = search
            self.execute(f"match Search /{search}/")
            self.normal_no_except(f"/{search}\n")
            self.post_cursor_move('/')
            return True
        if key in ['n', 'N']: 
            if self.last_search: 
                search_dir = {'n': '/', 'N': '?'}
                self.normal_no_except(f"{search_dir[key]}{self.last_search}\n")
            self.post_cursor_move(key)
            return True
        return False

    def get_keymap(self):
        return {}

    def onredraw(self):
        line = self.cur_cursor_line()
        super().onredraw()
        self.view_in(line)


class FileTreeBuffer(CursorLineBuffer): 
    def __init__(self, name, title):
        widgets = [
            TextWidget("", name=""),
        ]
        self.root_path = title
        self.tree = FileSystem().tree(title)
        self.views = []
        self.render_tree()
        self.select_item = self.tree
        self.syntax = "filetree"
        super().__init__(self.root, name, "filetree", file_tree_history)

    def on_key(self, key):
        if key in ['x']:
            self.on_close_dir()
            return True
        if key in ['m']:
            node = self.select_item
            self.call_custom_function(node)
            return True
        if key in ['u']: 
            self.goto_father()
            return True
        if super().on_key(key):
            return True
        return False

    def show_label(self, cmd):
        def on_select(item):
            line = item.bufpos[0] - 1
            if line < len(self.views): 
                self.select_item = self.views[line][1]
                if cmd == '<tab>': 
                    self.on_enter()
                else: 
                    self.redraw()
        from .quick_jump import JumpLines
        JumpLines([self.wid, on_select])

    def goto_father(self):
        father = self.select_item.father
        if father is None: return
        self.select_item = father
        self.redraw()

    def on_close_dir(self):
        father = self.select_item.father
        if father is None: return
        father.is_open = False
        self.goto_father()

    def on_move_brother(self, key):
        offset = {'J': 1, 'K': -1}[key]
        father = self.select_item.father
        if father is None: return 
        index = 0
        for idx, child in enumerate(father.child): 
            if child == self.select_item:
                index = idx
        newidx = index + offset
        if newidx >= 0 and newidx < len(father.child): 
            self.select_item = father.child[newidx]
            self.redraw()

    def on_enter(self):
        cur = self.get_lnum()
        if self.views[cur][2](self.views[cur][1]):
            self.close()

    def render_tree(self):
        def file_clicked(item):
            FileSystem().edit(item.fullpath)
            return True

        def dir_clicked(item):
            item.is_open = not item.is_open
            self.redraw()
            return False
             
        def _draw(root, indent):
            indent_str = " " * indent
            views= [] # [ ( string, tree, callback ) ] 
            for dir in root.dirs():
                name, fullpath = os.path.basename(dir.fullpath), dir.fullpath
                status_char = "-" if dir.is_open else '+'
                views.append(( f"{indent_str}{status_char} {name}/", dir, dir_clicked ))
                if dir.is_open:
                    child_views = _draw(dir, indent + 2)
                    views.extend(child_views)
            for file in root.files():
                name = os.path.basename(file.fullpath)
                views.append((f"{indent_str}  {name}", file, file_clicked))
            return views
        self.views= _draw(self.tree, 0)
        self.root = WidgetList("", [TextWidget(view[0]) for view in self.views])

    def onredraw(self):
        self.render_tree()
        super().onredraw()
        cur_lnum = self.get_lnum()
        self.view_in(cur_lnum)

    def post_cursor_move(self, char):
        cur_line = self.cur_cursor_line()
        self.select_item = self.views[cur_line][1]

    def get_lnum(self):
        cur_lnum = 0
        for idx, view in enumerate(self.views): 
            if view[1] == self.select_item: 
                cur_lnum = idx
        return cur_lnum

    def save(self):
        import copy
        history = {}
        history['cur'] = self.select_item
        history['win_view'] = self.eval("winsaveview()")
        return history

    def restore_view(self, history):
        self.select_item = history.value()['cur']
        self.redraw()
        self.execute(f"call winrestview({history.value()['win_view']})")

    def locate(self, fullpath):
        cur = self.tree.find_by_fullpath(fullpath)
        if cur is None: 
            print (f"Not find {fullpath} in current directory: {FileSystem().getcwd()}")
            return False
        self.tree.open_path(cur)
        self.select_item = cur
        self.redraw()
        return True

    def call_custom_function(self, node):
        # TODO:
        self.close()
        message = """ 
        You are calling custom method: "
        (a) for add a new file.
        (m) for move a file.
        (c) for copy a file.
        (d) for delete a file.
        """
        self.close()
        MessageWindow().set_markdowns([message])
        MessageWindow().show()
        ret = get_char_no_throw()
        if ret == "a": 
            MessageWindow().set_markdowns(["创建：\n输入文件名完整路径，目录以 '/' 结尾"])
            path = input_no_throw("", f"{node.fullpath}", "customlist,RemoteFileCommandComplete")
            if path and FileSystem().create_node(path): 
                vim.command(f"echow 'success creating {path}'")
        if ret == 'd': 
            if FileSystem().remove_node(node.fullpath): 
                vim.command(f"echow 'success remove {node.fullpath}'")
        MessageWindow().hide()

@vim_register(command="FileTree")
def FileTreeCommand(args):
    """ `FileTree` --- remote support.
    >>> FileTree
    show a file tree and explore the file system. 
    """
    cwd = FileSystem().getcwd()
    ff = FileTreeBuffer("filetree", cwd)
    ff.create()
    ff.show(popup=True)

@vim_register(keymap="<leader>F")
def FileTreeCurrentFile(args):
    cwd = FileSystem().getcwd()
    ff = FileTreeBuffer("filetree", cwd)
    ff.create()
    ff.show()
    file = CurrentEditFile(abs=True)
    if file and not ff.locate(file): 
        ff.close()
