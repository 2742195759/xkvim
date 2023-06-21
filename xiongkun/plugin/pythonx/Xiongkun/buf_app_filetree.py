import os
from .buf_app import WidgetBufferWithInputs, WidgetList, TextWidget, SimpleInput, WidgetBuffer, BufferHistory
from .func_register import vim_register
from .vim_utils import SetVimRegister, Normal_GI, Singleton, CurrentEditFile, Input
import vim
from functools import partial
from .log import debug
from .remote_fs import FileSystem

file_tree_history = BufferHistory("file_tree_history")

class DirectoryTree:
    def __init__(self, type, fullpath):
        self.child = []
        self.father = None
        self.type = type
        self.fullpath = fullpath
        self.is_open = False

    def add_child(self, tree):
        self.child.append(tree)
        tree.father = self

    def files(self):
        return [ item for item in self.child if item.type == 'file' ]

    def dirs(self):
        return [ item for item in self.child if item.type == 'dir' ]

    @staticmethod
    def from_dict(fullpath, content):
        this = DirectoryTree("dir", fullpath)
        for dir in content['dirs']:
            name, dircontent = dir
            if name.startswith('.'): continue
            this.add_child(DirectoryTree.from_dict(os.path.join(fullpath, name), dircontent))
        for file in content['files']: 
            if file.startswith('.'): continue
            this.add_child(DirectoryTree("file", os.path.join(fullpath, file)))
        return this

    def __eq__(self, other):
        return other.fullpath == self.fullpath

    def find_by_fullpath(self, fullpath):
        def _find(cur, fullpath):
            if fullpath == cur.fullpath: return cur
            for child in cur.child: 
                if fullpath.startswith(child.fullpath): 
                    return _find(child, fullpath)
        return _find(self, fullpath)

    def open_path(self, node):
        while node.father is not self: 
            node.father.is_open = True
            node = node.father

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
            search = Input("/")
            self.last_search = search
            self.execute(f"match Search /{search}/")
            self.normal_no_except(f"/{search}\n")
            return True
        if key in ['n', 'N']: 
            if self.last_search: 
                search_dir = {'n': '/', 'N': '?'}
                self.normal_no_except(f"{search_dir[key]}{self.last_search}\n")
            return True
        return False

    def get_keymap(self):
        return {}

    def onredraw(self):
        line = self.cur_cursor_line()
        super().onredraw()
        self.view_in(line)


class FileTreeBuffer(CursorLineBuffer): 
    def __init__(self, name, title, tree):
        widgets = [
            TextWidget("", name=""),
        ]
        self.root_path = title
        self.tree = DirectoryTree.from_dict(self.root_path, tree)
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
            self.call_custom_function()
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

    def on_cursor_move(self, char):
        super().on_cursor_move(char)
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
        history['tree'] = self.tree
        history['cur'] = self.select_item
        history['win_view'] = self.eval("winsaveview()")
        return history

    def restore_view(self, history):
        self.tree = history.value()['tree']
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

    def call_custom_function(self):
        # TODO:
        self.close()
        print ("You are calling custom method: ")
        print ("(m) for move   a file. ")
        print ("(c) for copy   a file. ")
        print ("(d) for delete a file. ")
        ret = Input(":")
        print ('you press ' + ret)

@Singleton
def FileTree():
    from .remote_fs import FileSystem
    tree = FileSystem().tree()
    return FileSystem().cwd, tree

@vim_register(command="FileTree")
def FileTreeCommand(args):
    """ `FileTree` --- remote support.
    >>> FileTree
    show a file tree and explore the file system. 
    """
    cwd, tree = FileTree()
    ff = FileTreeBuffer("filetree", cwd, tree)
    ff.create()
    ff.show(popup=True)

@vim_register(keymap="<leader>F")
def FileTreeCurrentFile(args):
    cwd, tree = FileTree()
    ff = FileTreeBuffer("filetree", cwd, tree)
    ff.create()
    ff.show()
    file = CurrentEditFile(abs=True)
    if not ff.locate(file): 
        ff.close()
