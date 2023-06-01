import os
from .buf_app import WidgetBufferWithInputs, WidgetList, TextWidget, SimpleInput, WidgetBuffer, BufferHistory
from .func_register import vim_register
from .vim_utils import SetVimRegister, Normal_GI, Singleton
import vim
from functools import partial
from .log import debug

class BrowserSearchBuffer(WidgetBufferWithInputs): 
    def __init__(self, name, title, hint=None):
        if not hint:
            hint = "输入enter键，在mac上打开网页:"
        widgets = [
            SimpleInput(prom="input", name="input"),
            TextWidget(hint, name=""),
        ]
        options = {
            'title': title, 
            'maxwidth': 100, 
            'minwidth': 50,
            'maxheight': 3, 
        }
        root = WidgetList("", widgets, reverse=False)
        super().__init__(root, name, None, options)

    def on_insert_input(self, key):
        if key == '<cr>': 
            text = self.widgets["input"].text
            self.on_enter(text)
            self.close()
            return True
        self.widgets["input"].on_type(key)
        self.redraw()
        return True

    def on_enter(self, text):
        raise NotImplementedError("Please implement the on_enter method")

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

class FileTreeBuffer(WidgetBuffer): 
    def __init__(self, name, title, tree):
        widgets = [
            TextWidget("", name=""),
        ]
        options = {
            'title': title, 
            'maxwidth': 100, 
            'minwidth':  50,
            'minheight': 30,
            'maxheight': 30, 
            'cursorline': 1,
        }
        self.root_path = title
        self.tree = DirectoryTree.from_dict(self.root_path, tree)
        self.views = []
        self.render_tree()
        self.select_item = self.tree
        super().__init__(self.root, name, file_tree_history, options)

    def on_key(self, key):
        if super().on_key(key):
            return True
        base_key = list(range(ord('a'), ord('z'))) + list(range(ord('A'), ord('Z')))
        base_key = list(map(chr, base_key))
        special_keys = [
            '<bs>', '<tab>', '<space>', '<c-w>', '<c-u>', '_', '-', '+', '=', '.', '/', '<cr>', '<left>', '<right>', "<c-a>", "<c-e>"
        ]
        insert_keys = base_key + special_keys
        if key in ['j', 'k']: 
            self.on_move_item(key)
            return True
        if key in ['J', 'K']:
            self.on_move_brother(key)
            return True
        if key in ['x']:
            self.on_close_dir()
            return True
        if key in ['m']:
            self.call_custom_function()
            return True
        if key in ['u']: 
            self.goto_father()
            return True
        if key in ['<cr>']: 
            self.on_enter()
            return True
        return False

    def on_close_dir(self):
        father = self.select_item.father
        if father is None: return
        father.is_open = False
        self.select_item = father
        self.redraw()

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
        cur = self.get_line_number()
        if self.views[cur][2](self.views[cur][1]):
            self.close()

    def view_in(self, lnum):
        self.execute(f":{lnum+1}")
        self.execute(f"normal zz")

    def render_tree(self):
        def file_clicked(item):
            from .remote_fs import FileSystem
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

    def get_lnum(self):
        cur_lnum = 0
        for idx, view in enumerate(self.views): 
            if view[1] == self.select_item: 
                cur_lnum = idx
        return cur_lnum

    def _get_window_size(self):
        height = len(self.root.widgets) + 1
        return height, int(vim.eval("winwidth(0)"))

    def on_move_item(self, char):
        self.execute(f'execute "normal! {char}"')
        lnum = self.get_line_number()
        if lnum < len(self.views): 
            self.select_item = self.views[lnum][1]

    def get_line_number(self):
        self.execute("let g:filetree_line_number=getpos('.')")
        return int(vim.eval("g:filetree_line_number")[1]) - 1

    def save(self):
        import copy
        history = {}
        history['tree'] = self.tree
        history['cur'] = self.select_item
        return history

    def restore_view(self, history):
        self.tree = history.value()['tree']
        self.select_item = history.value()['cur']
        self.redraw()

class GoogleSearch(BrowserSearchBuffer): 
    def __init__(self):
        super().__init__("Google", "Google搜索")

    def on_enter(self, text):
        vim.command(f"Google {text}")

class PaddleDocSearch(BrowserSearchBuffer): 
    def __init__(self):
        super().__init__("PaddleDoc", "Paddle文档搜索")

    def on_enter(self, text):
        vim.command(f"Pdoc {text}")


class TranslatorBuffer(WidgetBufferWithInputs): 
    def __init__(self):
        widgets = [
            SimpleInput(prom="input", name="input"),
            TextWidget("翻译:", name=""),
            TextWidget("", name="show"),
        ]
        options = {
            'title': "百度翻译", 
            'maxwidth': 100, 
            'minwidth': 50,
            'maxheight': 3, 
        }
        root = WidgetList("", widgets, reverse=False)
        super().__init__(root, "BaiduFanyi", None, options)

    def on_insert_input(self, key):
        if key == '<cr>': 
            return self.on_translate()
        self.widgets["input"].on_type(key)
        self.redraw()
        return True

    def on_translate(self): 
        from .converse_plugin import baidu_translate
        result = baidu_translate(self.widgets["input"].text)
        self.widgets["show"].text = result
        self.redraw()

    def on_exit(self):
        translated = self.widgets["show"].text
        SetVimRegister('"', translated)
        if vim.eval("mode()") == 'i': 
            # insert mode, we just insert the translated text
            vim.command(f'execute "normal i{translated}"')
            Normal_GI()


@vim_register(command="Fanyi")
def TestBaidufanyi(args):
    ff = TranslatorBuffer()
    ff.create()
    ff.show()
    
@vim_register(command="GoogleUI")
def TestGoogleUI(args):
    ff = GoogleSearch()
    ff.create()
    ff.show()

@vim_register(command="PdocUI")
def TestPdocUI(args):
    ff = PaddleDocSearch()
    ff.create()
    ff.show()
    
@Singleton
def FileTree():
    from .remote_fs import FileSystem
    tree = FileSystem().tree()
    return FileSystem().cwd, tree

@vim_register(command="FileTree")
def TestFileTree(args):
    cwd, tree = FileTree()
    ff = FileTreeBuffer("filetree", cwd, tree)
    ff.create()
    ff.show(popup=True)
