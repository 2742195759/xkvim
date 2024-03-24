import vim
from .cpp_parser import parse, swap, Selector
from .vim_utils import * 
from .func_register import *

@vim_register(name="ArgSwap")
def change_argument(list_int):
    def rep(line):
        ast = parse(line, "function")
        x, y = [ int(i) for i in list_int ]
        swap(Selector(ast)("$%d" % x), Selector(ast)("$%d" % y))
        return ast.to_string()
    ReplaceCurrentLine(rep)
