import subprocess
import os
from os import path as osp
import random
import threading
import json
from .sema import Sema
#from .log import log

def _ExpandCppDefinition(filename, start):# {{{
    """
    Expand the definition if True.
    return None, if it is not definition. may be a mistake.
    """
    try:
        with open(filename, "r") as fp :
            lines = fp.readlines()
        if start >= len(lines): return ""
        end = start
        while end < len(lines) and ";" not in lines[end] and ("{" not in lines[end] or "{{" in lines[end]):
            end += 1
        return "".join(lines[start:end+1])
    except:
        return ""# }}}

class Tokenizer:# {{{
    def __init__(self, code):
        self.cur_pos = 0
        self.code = code

    def is_keyword(self):
        keywords = ['const', 'static', 'inline']
        for kw in keywords:
            if self.code[self.cur_pos:self.cur_pos+len(kw)] == kw: 
                return kw
        return None

    def next(self):
        while True:
            # consume keywork
            kw = self.is_keyword()
            if kw: 
                self.consume(len(kw))
                return ("kw", kw)
            # peek id / operator
            c = self.peek(1)
            if c.isalpha() or c == "_" or self.peek(2) == "::": return ("id", self.consume_identifier())
            if c in ['(', "{", "<", "["]: return ("open", self.consume(1))
            if c in [",", ";", "="]: return ("char", self.consume(1))
            if c in ['/'] and self.peek(2) == "//": return ("comment", self.skip_to_char("\n"))
            self.consume(1)

    def peek_next(self):
        save = self.cur_pos
        t = self.next()
        self.cur_pos = save
        return t

    def consume_identifier(self):
        ret = []
        while self.peek(1).isalpha() or self.peek(1) == "_" or self.peek(2) == "::": 
            if self.peek(2) == "::": ret.append(self.consume(2))
            else: ret.append(self.consume(1))
        return "".join(ret)

    def peek(self, num):
        if self.cur_pos >= len(self.code): 
            raise RuntimeError("eof")
        return self.code[self.cur_pos: self.cur_pos+num]
    
    def back(self, num):
        self.cur_pos -= num
    
    def consume(self, num):
        tmp = self.peek(num)
        self.cur_pos += num
        return tmp
    
    def printf(self):
        i = self.cur_pos
        t = self.code
        print(t[:i] + '|' + t[i] + '|' + t[i+1:])

    def skip_to_char(self, char):
        chars = []
        while self.peek(1) == char: 
            chars.append(self.consume(1))
        return "".join(chars)

    def skip_to_identifier_start(self):
        while self.peek(1) == char: 
            self.consume(1)

    def skip_to_close(self):
        start = self.cur_pos
        pair = { "{": "}", "<": ">", "(": ")", "[":"]" }
        assert self.peek(1) in pair, "not a valid."
        open = self.peek(1)
        close = pair[open]
        self.cur_pos += 1
        level = 0
        while True:
            c = self.consume(1)
            if c == open: level += 1
            elif c == close: 
                if level == 0: break 
                level -= 1
        return self.code[start:self.cur_pos].strip()# }}}

class CppParser:# {{{
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def parse_parameters(self):
        if self.tokenizer.peek_next()[1] == '(': 
            self.tokenizer.skip_to_close()
            return
        raise RuntimeError("Not Definition.")

    def parse_template_optional(self):
        if self.tokenizer.peek_next()[1] == '<': 
            self.tokenizer.skip_to_close()

    def parse_body(self):
        while True:
            tok = self.tokenizer.next()
            if tok[1] in ['const'] : continue 
            if tok[1] in ['{'] : return 
            raise RuntimeError("Not Definition.")

    def parse_return_and_name(self):
        ids = []
        while True:
            tok = self.tokenizer.peek_next()
            if tok[0] == "id": 
                ids.append(tok[1])
                self.tokenizer.next()
            elif tok[0] == "open" and tok[1] in ["("]: 
                break 
            elif tok[0] == "open" and tok[1] in ["<"]: # return type can have template. ignore the template.
                ids[-1] += self.tokenizer.skip_to_close()
            elif tok[0] == "kw": 
                self.tokenizer.next()
            else:  
                raise RuntimeError("Not Definition.")
        if len(ids) < 2: 
            raise RuntimeError("Not Definition.")
        self.name = ids[-1]
        self.rtype = ids[0:-1]

    def parse_function_definition(self):
        self.parse_return_and_name()
        self.parse_template_optional()
        self.parse_parameters()
        self.parse_body()

    def parse_function_call(self):
        self.parse_return_and_name()
        self.parse_template_optional()
        self.parse_parameters()
        self.parse_body()

    def is_definition(self, identifier=None):
        try:
            self.parse_function_definition()
            if identifier: 
                return self.name.endswith("::" + identifier) or self.name == identifier
            return True
        except: 
            return False# }}}

def ParseCppDefinition(content, name=None):# {{{
    tokenizer = Tokenizer(content)
    fparser = CppParser(tokenizer)
    ret = fparser.is_definition(name)
    return ret# }}}

def test():# {{{
    code = _ExpandCppDefinition("/home/data/dl_framework/pytorch/c10/util/irange.h", 97)
    tokenizer = Tokenizer(code)
    fparser = CppParser(tokenizer)
    fparser.is_definition("irange")
    print(fparser.name)
    print(fparser.rtype)
    print(ParseCppDefinition(_ExpandCppDefinition("/home/data/Paddle/paddle/phi/kernels/matmul_kernel.h", 42)))
    print(ParseCppDefinition(_ExpandCppDefinition("/home/data/Paddle/paddle/fluid/framework/ir/graph_pattern_detector.cc", 1815)))# }}}

def GetOffset(x, y, content):# {{{
    cur_line = 1
    cur_col = 0
    for idx, c in enumerate(content): 
        if c == '\n': 
            cur_line += 1
            cur_col = 0
            continue
        cur_col += 1
        if x == cur_line and y == cur_col:  
            return idx
    assert False# }}}

def TopLevelHeader():# {{{
    """ get the cpp top level position. based by rule.
    """
    from . import vim_utils
    x, y = vim_utils.GetCursorXY()
    file = vim_utils.CurrentEditFile(True)
    with open(file, "r") as fp :
        lines = fp.readlines()
    nest_level = 0
    content = "".join(lines)
    off = GetOffset(x, y, content)
    cur_line = 1
    lst_top = -1
    for idx, c in enumerate(content):
        if c == '\n': cur_line += 1
        if c == '{' : 
            if nest_level == 0: lst_top = idx
            nest_level += 1# }}}

def IsCppDefinition(loc, id_name=None):# {{{
    """
    Expand the definition if True.
    return None, if it is not definition. may be a mistake.
    """
    code = _ExpandCppDefinition(osp.abspath(loc.getfile()), loc.getline()-1)
    #log("Expanded: ", code)
    if len(code.split("\n")) > 30: return False
    return ParseCppDefinition(code, id_name)# }}}

class CppSema(Sema):
    def __init__(self):
        pass
    def is_function_definition(self, loc, id_name=None):
        return IsCppDefinition(loc, id_name)

if __name__ == "__main__":
    test()
