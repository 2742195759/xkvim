from tree_sitter import Language, Parser
from os.path import expanduser
import os
import sys

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

    def is_definition(self, name, linenr, contents, language): 
        try:
            func = getattr(self, "for_each_definition_" + language + "_do")
        except: 
            raise NotImplementedError()
        for (node_type, def_node, name_node) in func(contents): 
            #print ("Found first: ", node_type, name_node.start_point[0], name_node.text)
            #sys.stdout.flush()
            def_text = name_node.text.decode("utf-8")
            if name_node.start_point[0] == linenr and def_text.split("::")[-1] == name: 
                return True
            if name_node.start_point[0] == linenr and name is None:
                return True
        return False

    def for_each_definition_python_do(self, contents):
        pass

    def get_field(self, node, name):
        fields = name.split('.')
        current_node = node
        for f in fields: 
            if f.startswith('@'):  # get children with type: 
                for n in current_node.children:
                    if n.type == f[1:]: 
                        current_node = n
            elif f.startswith('?'):  # get children with type: 
                maybe_node = current_node.children_by_field_name(f)
                if len(maybe_node) == 0: continue
                current_node = maybe_node[0]
            else: 
                current_node = current_node.children_by_field_name(f)
                if len(current_node) == 0: return None
                current_node = current_node[0]
        return current_node

    def for_each_definition_cpp_do(self, contents):
        query_str = """
        ((function_declarator) @function_decl)
        ((function_definition) @function)
        ((field_declaration) @field)
        ((template_declaration) @template)
        ((class_specifier) @class_def)
        ((struct_specifier) @class_def)
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

if __name__ == "__main__":
    contents = """
class PADDLE_API AAAA {
    int func() {
        return 1;
    }
};

struct CCCC {};

void AAAA::BBBB(){
    return ;
}
    """
    contents = contents.split("\n")
    test_manager = TreeSitterManager()
    for node in test_manager.for_each_definition_cpp_do(contents): 
        print (node[1].type, node[1].text)
