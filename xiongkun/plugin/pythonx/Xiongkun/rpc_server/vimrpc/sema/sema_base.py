# interface of Cpp
class Sema:
    def __init__(self):
        pass
    def is_function_definition(self, loc, id_name=None):
        return False
    def is_class_definition(self, loc, id_name=None):
        return False

def GetTextFromLocation(loc):
    with open(loc.file, "r") as fp :
        lines = fp.readlines()
    if loc.line < len(lines): 
        return lines[loc.line]
    return None
