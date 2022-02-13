import vim
from .cpp_parser import parse

def test_parse():
    line = vim.eval("getline('.')")
    ast = parse(line, "function")
    print(ast.to_string())

