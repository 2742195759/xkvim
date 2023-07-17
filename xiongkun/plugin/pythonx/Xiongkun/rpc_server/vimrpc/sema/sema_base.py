from tree_sitter import Language, Parser
from os.path import expanduser
import os

HOME_PREFIX = expanduser("~")

# interface of Cpp
class Sema:
    def __init__(self):
        pass
    def is_function_definition(self, loc, id_name=None):
        return False
    def is_class_definition(self, loc, id_name=None):
        return False

def GetTextFromLocation(loc):
    try:
        with open(loc.file, "r") as fp :
            lines = fp.readlines()
        if loc.line < len(lines): 
            return lines[loc.line]
    except: 
        return None

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
            func = getattr(self, "is_definition_" + language)
        except: 
            raise NotImplementedError()
        return func(name, contents)

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
        ((function_declarator) @function_decl)
        ((function_definition) @function)
        ((field_declaration) @field)
        ((template_declaration) @template)
        """
        parser = self.get_parser("cpp")
        query = self.get_query(query_str, "cpp")
        if isinstance(contents, list):
            source_code = bytes("\n".join(contents), "utf-8")
            node = parser.parse(source_code).root_node
        else:
            raise NotImplementedError()
        for node in query.captures(node): 
            if name is None: return True
            if node[1] == 'function' and self.get_field(node[0], 'declarator.declarator') == name: 
                return True
            if node[1] == 'function_decl' and self.get_field(node[0], 'declarator') == name: 
                return True
            if node[1] == 'field' and self.get_field(node[0], 'declarator') == name: 
                return True
            if node[1] == 'assignment' and self.get_field(node[0], 'left') == name: 
                return True
            if node[1] == 'template':
                for n in node[0].children:
                    if n.type == "declaration" and self.get_field(n, "declarator.declarator.declarator") == name: 
                        return True
                return False
        return False

