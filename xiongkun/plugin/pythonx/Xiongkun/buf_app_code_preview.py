from tree_sitter import Language, Parser
import os
import os
from .buf_app import WidgetBufferWithInputs, WidgetList, TextWidget, SimpleInput, WidgetBuffer, BufferHistory
from .func_register import vim_register
from .vim_utils import SetVimRegister, Normal_GI, Singleton, CurrentEditFile, input_no_throw, get_char_no_throw, GetAllLines, HOME_PREFIX, GetCursorXY
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
            'tree-sitter-cpp',
        ]
        self._install_()
        Language.build_library(
          # Store the library in the `build` directory
          'build/my-languages.so',
          # Include one or more languages
          [ os.path.join(HOME_PREFIX, item) for item in self.to_install ]
        )

    def get_parser(self, language):
        LANGUAGE = Language('build/my-languages.so', language)
        parser = Parser()
        parser.set_language(LANGUAGE)
        return parser

    def get_query(self, query_str, language):
        LANGUAGE = Language('build/my-languages.so', language)
        query = LANGUAGE.query(query_str)
        return query

    def is_definition(self, name, contents, language): 
        try:
            func = getattr(self, "class_layout_" + language)
        except: 
            raise NotImplementedError()
        return func(contents)

    def is_definition_python(self, name, contents):
        pass

    def get_field(self, node, name):
        fields = name.split('.')
        current_node = node
        for f in fields: 
            current_node = current_node.children_by_field_name(f)
            if len(current_node) == 0: return None
            current_node = current_node[0]
        return current_node.text.decode("utf-8")

    def is_definition_cpp(self, name, contents):
        query_str = """
        ((function_definition) @function)
        ((field_declaration) @field)
        """
        parser = self.get_parser("cpp")
        query = self.get_query(query_str, "cpp")
        if isinstance(contents, list):
            source_code = bytes("\n".join(contents), "utf-8")
            node = parser.parse(source_code).root_node
        else:
            raise NotImplementedError()
        for node in query.captures(node): 
            if node[1] == 'function' and self.get_field(node[0], 'declarator.declarator') == name: 
                return True
            if node[1] == 'field' and self.get_field(node[0], 'declarator') == name: 
                return True
            if node[1] == 'assignment' and self.get_field(node[0], 'left') == name: 
                return True
        return False

    def class_layout(self, contents, language): 
        try:
            func = getattr(self, "class_layout_" + language)
        except: 
            raise NotImplementedError()
        return func(contents)

    def class_layout_python(self, contents):
        query_str = """
        (module ((function_definition) @function))
        (class_definition) @class
        """
        parser = self.get_parser("python")
        query = self.get_query(query_str, "python")
        if isinstance(contents, list):
            source_code = bytes("\n".join(contents), "utf-8")
            node = parser.parse(source_code).root_node
        else:
            raise NotImplementedError()

        root = DirectoryTree("dir", "root")
        for node in query.captures(node): 
            if node[1] == "class":
                this = DirectoryTree("dir", "class: " + node[0].child_by_field_name('name').text.decode('utf-8'), (node[0].start_point, node[0].end_point))
                for field in node[0].children_by_field_name('body')[0].named_children: 
                    if field.type == 'function_definition':
                        this.add_child(DirectoryTree("file", "method: " + field.child_by_field_name('name').text.decode('utf-8'), (field.start_point, field.end_point)))
                this.is_open = True
                root.add_child(this)
            elif node[1] == "function":
                root.add_child(DirectoryTree("file", "function: " + node[0].child_by_field_name('name').text.decode('utf-8'), (node[0].start_point, node[0].end_point)))
        return root

    def for_each_definition_cpp_do(self, contents):
        query_str = """
        ((function_declarator) @function_decl)
        ((function_definition) @function)
        ((field_declaration) @field)
        ((template_declaration) @template)
        ((class_specifier) @class_def)
        """
        parser = self.get_parser("cpp")
        query = self.get_query(query_str, "cpp")
        if isinstance(contents, list):
            source_code = bytes("\n".join(contents), "utf-8")
            node = parser.parse(source_code).root_node
        else:
            raise NotImplementedError()
        type2field = {
            'function': 'declarator.declarator',
            'function_decl': 'declarator',
            'field': 'declarator',
            'template': '@declaration.declarator.declarator.declarator',
            'class_def': 'name',
        }
        for node in query.captures(node): 
            n = self.get_field(node[0], type2field[node[1]])
            if n is None: continue
            yield node[1], node[0], n

    def class_layout_cpp(self, contents):
        root = DirectoryTree("dir", "root")
        unique_set = set()
        for (node_type, def_node, name_node) in self.for_each_definition_cpp_do(contents): 
            def_text = name_node
            if def_node.start_point in unique_set:
                continue
            unique_set.add(def_node.start_point)
            if node_type == "class_def":
                this = DirectoryTree("dir", "class: " + def_text, (def_node.start_point, def_node.end_point))
                for field in def_node.children_by_field_name('body')[0].named_children: 
                    if field.type == 'function_definition':
                        print ("Insert:", id(field), field)
                        unique_set.add(field.start_point)
                        this.add_child(DirectoryTree("file", "method: " + field.child_by_field_name('declarator').text.decode('utf-8'), (field.start_point, field.end_point)))
                for field in def_node.children_by_field_name('body')[0].named_children: 
                    if field.type == 'field_declaration':
                        unique_set.add(field.start_point)
                        this.add_child(DirectoryTree("file", "member: " + field.text.decode('utf-8'), (field.start_point, field.end_point)))
                this.is_open = True
                root.add_child(this)
            elif node_type in ["function", "template"]:
                root.add_child(DirectoryTree("file", "function: " + def_node.child_by_field_name('declarator').text.decode('utf-8'), (def_node.start_point, def_node.end_point)))
        return root

class CodeTreeBuffer(CursorLineBuffer):
    def __init__(self, name, lines, language):
        widgets = [
            TextWidget("", name=""),
        ]
        self.root_path = ""
        self.tree:DirectoryTree = TreeSitterManager().class_layout(lines, language)
        self.views = []
        self.render_tree()
        self.select_item = self.tree
        self.syntax = "code_preview"
        super().__init__(self.root, name, "code preview", None)

    def locate_by_pos(self, line, col):
        self.select_item = self.tree
        line -= 1 # 0-based
        for item in self.tree.visit_bfs():
            start, end = item.extra_data
            start_line, _ = start
            end_line, _ = end
            if line >= start_line and line <= end_line: 
                self.select_item = item
                break
        self.redraw()

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
            line_nr = item.extra_data[0][0]
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
        if cur_line < len(self.views):
            self.select_item = self.views[cur_line][1]

    def get_lnum(self):
        cur_lnum = 0
        for idx, view in enumerate(self.views): 
            if view[1] == self.select_item: 
                cur_lnum = idx
        return cur_lnum

@vim_register(command="TagList", keymap="<leader>T")
def CodePreviewCurrentFile(args):
    lines = GetAllLines()
    x, y = GetCursorXY()
    language = vim.eval("&ft")
    try:
        ff = CodeTreeBuffer("code preview", lines, language)
    except NotImplementedError: 
        print (f"Don't Implement taglist for {language}.")
        return
    ff.create()
    ff.show()
    ff.locate_by_pos(x, y)

if __name__ == "__main__":
    with open("/home/xiongkun/tmp.py") as f:
        lines = f.readlines()
    lines = [line.rstrip() for line in lines]
    ts = TreeSitterManager()
    result = ts.class_layout(lines)
    breakpoint() 
