from .node import *
from ply.lex import lex
from ply.yacc import yacc

class Selector: 
    def __init__(self, root=None):
        self.current = root

    def set_root(self, root):
        """
        root : Node 
        """
        self.current = root
        return self

    def __call__(self, selector):
        self.current = select(self.current, selector)
        return self

    def value(self):
        return self.current

def _find_idx_of_child(cur):
    s = -1
    for idx, node in enumerate(cur.father.childs):
        if id(node) == id(cur): s = idx
    assert (s >= 0)
    return s

def replace(cur, func):
    """ 
    replace current node with func(cur)
    func receive a node and return a modified node.
    """
    s = _find_idx_of_child(cur)
    tmp = func(cur)
    cur.father[s] = tmp
    return tmp

def swap(a, b):
    """ 
    swap current node with func(cur)
    """
    idx_a = _find_idx_of_child(a)
    idx_b = _find_idx_of_child(b)
    tmp = a
    a.father.childs[idx_a] = b
    b.father.childs[idx_b] = tmp

"""
usage: 
    s = Selecter().set_root(root)
    s("$0")
"""

tokens = ( 'NUMBER', 'CHILD', 'NEXT' )

t_ignore = ' \t'
t_CHILD = r'\$'
t_NEXT = r'\.'

def t_NUMBER(t):
    r'[0-9\-][0-9]*'
    t.value = int(t.value)
    return t

# Error handler for illegal characters
def t_error(t):
    print(f'Illegal character {t.value[0]!r}')
    t.lexer.skip(1)


# --- Parser

# Write functions for each grammar rule which is
# specified in the docstring.

def p_root(p):
    '''
    root : selects
    '''
    p[0] = p[1]

def p_selects_1(p):
    '''
    selects : select NEXT selects
    '''
    p[0] = p[1] + [p[3]]

def p_selects_2(p):
    '''
    selects : select
    '''
    p[0] = [p[1]]

def p_select(p):
    '''
    select : childselect
    '''
    p[0] = p[1]

def p_childselect(p):
    '''
    childselect : CHILD NUMBER
    '''
    p[0] = ['child', p[2]]

def p_error(p):
    print(f'Syntax error at {p.value!r}')

def select(root, selector):
    # Parse an expression
    """ 
    don't support concurrent
    return: Node or it's subclass
    """
    # Build the lexer object
    lexer = lex()
    # Build the parser
    parser = yacc()
    selects =  parser.parse(selector)
    assert (isinstance(selects, list))
    for s in selects:
        if s[0] == "child":
            if s[1] > 0: root = root.childs[s[1] - 1]
            else : 
                while (s[1] != 0):
                    s[1] = s[1] + 1
                    root = root.father
    return root
