# interface of Cpp
class Sema:
    def __init__(self):
        pass
    def is_function_definition(self, loc, id_name=None):
        return False
    def is_class_definition(self, loc, id_name=None):
        return False


