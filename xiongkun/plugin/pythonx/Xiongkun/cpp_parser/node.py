import os

class Node : 
    def __init__(self):
        self.name = ""
        self.type = "node"
        self.text = ""
        self.start_pos = (-1, -1) # line, column
        self.end_pos = (-1, -1) # line, column
        self.childs = []
        self.father = None

    def to_string(self):
        return "node()"

    def append_child(self, child):
        self.childs.append(child)
        child.father = self

    def append_childs(self, childs):
        for i in childs:
            self.append_child(i)

    def __setitem__(self, idx, current):
        self.childs[idx] = current
        current.father = self
        
    def __getitem__(self, idx):
        return self.childs[idx]

    def __len__(self):
        return len(self.childs)

class FuncNode(Node):
    def __init__(self):
        super(FuncNode, self).__init__()
        self.type = "function"

    def to_string(self):
        return ("%s( %s )"% (self.name, ", ".join( [ i.to_string() for i in self.childs ] )))

class IdNode(Node): 
    def __init__(self):
        super(IdNode, self).__init__()
        self.type = "id"

    def to_string(self):
        return ("%s" % self.name)

class WrapperNode(Node):
    def __init__(self, node, fmt_str):
        super(WrapperNode, self).__init__()
        self.type = "wrapper"
        self.fmt = fmt_str
        self.node = node

    def to_string(self):
        return (self.fmt % (self.node.to_string()))
