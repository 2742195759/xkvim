# -----------------------------------------------------------------------------
# example.py
#
# Example of using PLY To parse the following simple grammar.
#
#   expression : term PLUS term
#              | term MINUS term
#              | term
#
#   term       : factor TIMES factor
#              | factor DIVIDE factor
#              | factor
#
#   factor     : NUMBER
#              | NAME
#              | PLUS factor
#              | MINUS factor
#              | LPAREN expression RPAREN
#
# -----------------------------------------------------------------------------

from ply.lex import lex
from ply.yacc import yacc
from .node import *
from .selecter import Selector

# --- Tokenizer

# All tokens must be named in advance.
tokens = ( 'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'LPAREN', 'RPAREN',
           'NAME', 'NUMBER', 'SEMICOLON', 'COMMA' )

# Ignored characters
t_ignore = ' \t'

# Token matching rules are written as regexs
t_PLUS = r'\+'
t_MINUS = r'-'
t_TIMES = r'\*'
t_DIVIDE = r'/'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_SEMICOLON = r'\;'
t_COMMA = r'\,'

# A function can be used if there is an associated action.
# Write the matching regex in the docstring.
def t_NAME(t):
    r'[a-zA-Z_][a-zA-Z0-9_:]*'
    #t.lexer.lexpos += len(t.value)
    return t

def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t

# Ignored token with an action associated with it
def t_ignore_newline(t):
    r'\n+'
    t.lexer.lineno += t.value.count('\n')

# Error handler for illegal characters
def t_error(t):
    print(f'Illegal character {t.value[0]!r}')
    t.lexer.skip(1)

# --- Parser
# Write functions for each grammar rule which is
# specified in the docstring.

start = 'root'

def set_pos(node, p, s, e):
    node.start_pos = p.linespan(s)[0], p.lexspan(s)[0]
    node.end_pos = p.linespan(e)[1], p.lexspan(e)[1]

def p_root(p):
    '''
    root : function SEMICOLON
    '''
    p[0] = p[1]

def p_function(p):
    '''
    function : NAME LPAREN args RPAREN
    '''
    p[0] = FuncNode()
    set_pos(p[0], p, 1, 4)
    p[0].name = p[1]
    p[0].append_childs(p[3])

def p_args_recur(p):
    '''
    args : arg COMMA args
    '''
    # return list
    p[0] = [p[1]] + p[3]

def p_args_single(p):
    '''
    args : arg
    '''
    p[0] = [p[1]]
    
def p_arg(p):
    '''
    arg : function 
        | identifier
    '''
    p[0] = p[1]

def p_identifier(p):
    '''
    identifier : NAME
    '''
    p[0] = IdNode()
    p[0].name = p[1]
    p[0].start_pos = p.linespan(0)[0], p.lexspan(0)[0]
    p[0].end_pos = p.linespan(0)[1], p.lexspan(0)[1] + len(p[1]) - 1
    
def p_error(p):
    print(f'Syntax error at {p.value!r}')

def parse (source, start_at='root'): 
    global start
    start = start_at

    # Build the lexer object
    lexer = lex()
    # Build the parser
    parser = yacc()
    # Parse an expression
    ast = parser.parse(source, tracking=True)
    return ast
    

def test():
    source = ''' GLOO_ALL_GATHER_CASE(framework::proto::VarType::FP32, tmp(yes), gloo_wrapper) '''
    ast = parse (source, 'function')
#    x = selecter.replace(Selector(ast)("$1").value(), lambda x: WrapperNode(x, "( %s )"))
#    y = Selector(ast)("$2").value()
#    selecter.swap(x, y)
    def print_debug(node):
        print ("DEUB:")
        print (node.to_string())
        print (node.start_pos)
        print (node.end_pos)
        print (source[node.start_pos[1]: node.end_pos[1]+1])

    print_debug(ast[2])

if __name__ == "__main__":
    test()
