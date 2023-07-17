from tree_sitter import Language, Parser
import os
import os
from .buf_app import WidgetBufferWithInputs, WidgetList, TextWidget, SimpleInput, WidgetBuffer, BufferHistory
from .func_register import vim_register
from .vim_utils import SetVimRegister, Normal_GI, Singleton, CurrentEditFile, input_no_throw, get_char_no_throw, GetAllLines, HOME_PREFIX
import vim
from functools import partial
from .log import debug
from .remote_fs import FileSystem
from .windows import MessageWindow
from .buf_app_filetree import CursorLineBuffer
from .remote_fs import DirectoryTree

@Singleton
class TreeSitterManager: 
    def _install_(self):
        for item in self.to_install: 
            if not os.path.isdir(os.path.join(HOME_PREFIX, item)): 
                os.system(f"cd {HOME_PREFIX} && git clone https://github.com/tree-sitter/{item}")

    def __init__(self):
        self.to_install = [
            'tree-sitter-python',
        ]
        self._install_()
        Language.build_library(
          # Store the library in the `build` directory
          'build/my-languages.so',
          # Include one or more languages
          [ os.path.join(HOME_PREFIX, item) for item in self.to_install ]
        )

        self.PY_LANGUAGE = Language('build/my-languages.so', 'python')
        parser = Parser()
        parser.set_language(self.PY_LANGUAGE)
        self.parser = parser
        self.trees = {}

    def _add_tree(self, filepath, tree): 
        self.trees[filepath] = tree
    
    def add_document(self, filepath): 
        source_code = None
        if not os.path.isfile(filepath): 
            return False

        with open(filepath, "rb") as f:
            source_code = b"".join(f.readlines())
        tree = self.parser.parse(source_code)
        self._add_tree(filepath, tree)
        return True

    def class_layout(self, contents):
        query_str = """
        (module ((function_definition) @function))
        (class_definition) @class
        """
        #(function definition) @function
        query = self.PY_LANGUAGE.query(query_str)
        if isinstance(contents, list):
            source_code = bytes("\n".join(contents), "utf-8")
            node = self.parser.parse(source_code).root_node
        else:
            node = self.trees[contents].root_node
        root = DirectoryTree("dir", "root")
        for node in query.captures(node): 
            if node[1] == "class":
                this = DirectoryTree("dir", "class: " + node[0].child_by_field_name('name').text.decode('utf-8'), node[0].start_point)
                for field in node[0].children_by_field_name('body')[0].named_children: 
                    if field.type == 'function_definition':
                        this.add_child(DirectoryTree("file", "method: " + field.child_by_field_name('name').text.decode('utf-8'), field.start_point))
                this.is_open = True
                root.add_child(this)
            elif node[1] == "function":
                root.add_child(DirectoryTree("file", "function: " + node[0].child_by_field_name('name').text.decode('utf-8'), node[0].start_point))
        return root

    def query(self, filepath, query_str):
        query = self.PY_LANGUAGE.query(query_str)
        node = self.trees[filepath].root_node
        results = query.captures(node)
        outputs = []
        for result in results: 
            outputs.append(result[0].text)
        return outputs

class CodeTreeBuffer(CursorLineBuffer):
    def __init__(self, name, lines):
        widgets = [
            TextWidget("", name=""),
        ]
        self.root_path = ""
        self.tree = TreeSitterManager().class_layout(lines)
        self.views = []
        self.render_tree()
        self.select_item = self.tree
        self.syntax = "filetree"
        super().__init__(self.root, name, "code preview", None)

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
            line_nr = item.extra_data[0]
            vim.command(f"{line_nr + 1}")
            return True

        def dir_clicked(item):
            item.is_open = not item.is_open
            self.redraw()
            return False
             
        def _draw(root, indent):
            indent_str = " " * indent
            views= [] # [ ( string, tree, callback ) ] 
            for dir in root.dirs():
                name = dir.fullpath
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
                FileSystem().edit(path, True)
        if ret == 'd': 
            if FileSystem().remove_node(node.fullpath): 
                vim.command(f"echow 'success remove {node.fullpath}'")
        MessageWindow().hide()

@vim_register(command="TagList", keymap="<leader>c")
def CodePreviewCurrentFile(args):
    lines = GetAllLines()
    ff = CodeTreeBuffer("code preview", lines)
    ff.create()
    ff.show()

if __name__ == "__main__":
    with open("/home/xiongkun/tmp.py") as f:
        lines = f.readlines()
    lines = [line.rstrip() for line in lines]
    ts = TreeSitterManager()
    result = ts.class_layout(lines)
    breakpoint() 
