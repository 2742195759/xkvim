import os
from .buf_app import WidgetBufferWithInputs, WidgetList, TextWidget, SimpleInput, WidgetBuffer, BufferHistory, MultiSelectWidget
from .func_register import vim_register
from .vim_utils import SetVimRegister, Normal_GI, Singleton
import vim
from functools import partial
from .log import debug
from .buf_app_filetree import CursorLineBuffer
from .remote_fs import FileSystem
from .windows import GPW, PreviewWindow

class GitCommitter(CursorLineBuffer):
    def __init__(self, name="GitCommitter"):
        self.mult = MultiSelectWidget(*self.git_stage_files())
        self.widgets = WidgetList("", [
            TextWidget("Press space to select: "),
            self.mult,
        ])
        super().__init__(self.widgets, name, "Git Committer")

    def git_stage_files(self):
        lines = FileSystem().eval("git status -s")
        files = []
        selected = {}
        for line in lines:
            line = line.rstrip()
            type, file = line[:2], line[3:]
            if type == "??"  : file = f"untrace | {file}"
            if type[0] == " ": file = f"unstage | {file}"
            if type[1] == " ": file = f"stage   | {file}"
            selected[file] = False
            if type[1] == " ":
                selected[file] = True
            files.append(file)
        return files, selected

    def git_add(self, item):
        FileSystem().command(f"git add {item}")

    def git_unstage(self, item):
        FileSystem().command(f"git restore --stage {item}")

    def on_enter(self):
        for item in self.mult.get_selected(): 
            self.git_add(item[10:])
        for item in self.mult.get_not_selected(): 
            if "untrace" not in item: self.git_unstage(item[10:])
        self.mult.reset(*self.git_stage_files())
        self.redraw()

    def on_jump_label(self):
        print ("not implement.")

    def on_key(self, key):
        if key in ['j', 'k'] and not GPW.hidden:
            { 'j': GPW.page_down, 'k': GPW.page_up }[key]()
            return True
        if key == "<space>":
            number = self.get_line_number()
            if number < 1: return True
            self.mult.onselect(number - 1)
            self.redraw()
            return True
        if key == "p": 
            """preview the changes"""
            number = self.get_line_number()
            if number < 1: return True
            self.git_show(self.mult.items[number-1])
            return True
        if super().on_key(key):
            return True
        return False

    def git_show(self, item):
        if "unstage" in item: 
            lines = FileSystem().eval(f"git diff {item[10:]}")
        elif "stage" in item: 
            lines = FileSystem().eval(f"git diff --cached {item[10:]}")
        self.preview(item[10:], lines)
        

    def preview(self, file, lines):
        position = { 'zindex': 1000, }
        GPW.set_showable([
            PreviewWindow.ContentItem(file, lines, "magit", 1, position)
        ])
        GPW.trigger()

@vim_register(command="GitCommit")
def StartGitCommit(args):
    commit = GitCommitter()
    commit.create()
    commit.show()
