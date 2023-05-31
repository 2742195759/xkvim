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

class FileTreeBuffer(WidgetBuffer): 
    def __init__(self, name, title, tree):
        widgets = [
            TextWidget("", name=""),
        ]
        options = {
            'title': title, 
            'maxwidth': 100, 
            'minwidth': 50,
            'maxheight':20, 
            'cursorline': 1,
        }
        self.tree = tree
        self.root_path = title
        self.onclicked = []
        self.opened = set()
        self.set_tree()
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
        if key in ['<cr>']: 
            self.on_enter()
            return True
        return False

    def on_enter(self):
        cur = self.get_line_number()
        if self.onclicked[cur]():
            self.close()

    def view_in(self, lnum):
        self.execute(f":{lnum+1}")
        self.execute(f"normal zz")

    def set_tree(self):
        def file_clicked(filepath):
            from .remote_fs import FileSystem
            FileSystem().edit(filepath)
            return True

        def dir_clicked(dirpath):
            if dirpath in self.opened: 
                self.opened.remove(dirpath)
            else: 
                self.opened.add(dirpath)
            cur_lnum = self.get_line_number()
            self.set_tree()
            self.redraw()
            self.view_in(cur_lnum)
            return False
             
        def _draw(root, prefix, indent):
            indent_str = " " * indent
            ret = []
            click = []
            for dir in root['dirs']:
                name, content = dir
                if name.startswith('.'): continue
                fullpath = os.path.join(prefix, name)
                is_open = fullpath in self.opened
                status_char = "-" if is_open else '+'
                ret.append(TextWidget(f"{indent_str}{status_char} {name}/"))
                click.append(partial(dir_clicked, fullpath))
                if fullpath in self.opened: 
                    dir_ret, dir_click = _draw(content, fullpath + '/', indent + 2)
                    ret.extend(dir_ret)
                    click.extend(dir_click)
            for file in root['files']: 
                if file.startswith('.'): continue
                ret.append(TextWidget(f"{indent_str}  {file}"))
                click.append(partial(file_clicked, os.path.join(prefix, file)))
            return ret, click

        texts, click = _draw(self.tree, self.root_path, 0)
        debug(texts)
        assert len(texts) == len(click)
        self.onclicked = click
        self.root = WidgetList("", texts, reverse=False)

    def _get_window_size(self):
        height = len(self.root.widgets) + 1
        return height, int(vim.eval("winwidth(0)"))

    def on_move_item(self, char):
        self.execute(f'execute "normal! {char}"')

    def get_line_number(self):
        self.execute("let g:filetree_line_number=getpos('.')")
        return int(vim.eval("g:filetree_line_number")[1]) - 1

    def save(self):
        import copy
        history = {}
        history['lnum'] = self.get_line_number()
        history['opened'] = copy.deepcopy(self.opened)
        return history

    def restore_view(self, history):
        self.opened = history.value()['opened']
        self.set_tree()
        self.onredraw() # redraw to restore view.
        self.view_in(history.value()['lnum'])
        return history

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
