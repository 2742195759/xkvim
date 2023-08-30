import os
from .buf_app import WidgetBufferWithInputs, WidgetList, TextWidget, SimpleInput, WidgetBuffer, BufferHistory, MultiSelectWidget
from .func_register import vim_register
from .vim_utils import SetVimRegister, Normal_GI, Singleton, input_no_throw, escape
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
        self.syntax = "gitcommitter"
        super().__init__(self.widgets, name, "Git Committer")

    def git_stage_files(self):
        lines = FileSystem().eval("git status -s")
        files = []
        selected = {}
        for line in lines:
            line = line.rstrip()
            type, file = line[:2], line[3:]
            if   type == "??"  : file = f"untrace | {file}"
            elif type[1] != " ": file = f"unstage | {file}"
            elif type[1] == " ": file = f"stage   | {file}"
            selected[file] = False
            if type[1] == " ":
                selected[file] = True
            files.append(file)
        files.sort(key=lambda x: x[0][0:7])
        return files, selected

    def git_add(self, item):
        FileSystem().command(f"git add {item}")

    def git_unstage(self, item):
        FileSystem().command(f"git reset HEAD -- {item}")

    def on_space(self):
        for item in self.mult.get_selected(): 
            self.git_add(item[10:])
        for item in self.mult.get_not_selected(): 
            if "untrace" not in item: self.git_unstage(item[10:])
        self.mult.reset(*self.git_stage_files())
        self.redraw()

    def on_jump_label(self):
        print ("not implement.")

    @property
    def select_item(self):
        number = self.cur_cursor_line()
        if number < 1: return True
        return self.mult.items[number-1]

    def on_key(self, key):
        if key in ['j', 'k'] and not GPW.hidden:
            { 'j': GPW.page_down, 'k': GPW.page_up }[key]()
            return True
        if key == "<space>":
            number = self.cur_cursor_line()
            if number < 1: return True
            self.mult.onselect(number - 1)
            GPW.hide()
            self.redraw()
            return True
        if key == "<cr>":
            GPW.hide()
            self.on_space()
            return True
        if key == "p": 
            """preview the changes"""
            number = self.cur_cursor_line()
            if number < 1: return True
            self.git_show(self.mult.items[number-1])
            return True
        if key == "c": 
            self.commit()
            return True
        if key == 'D': 
            self.remove(self.select_item)
        if key == "e": 
            self.start_edit()
            return True
        if super().on_key(key):
            return True
        return False

    def commit(self):
        message = input_no_throw("Commit Message: ")
        if message is None: 
            return
        self.close()
        message = escape(message, "\"'\\")
        if FileSystem().command(f'git commit -m "{message}"'):
            print ("Success.")

    def remove(self, item):
        prompt = ""
        command = ""
        filename = item[10:]
        if "untrace" in item:
            prompt = f"You will remove untrace file `{filename}`, press `yes` to confirm: "
            command = f"rm -rf {filename}"
        elif "unstage" in item:
            prompt = f"You will remote all changes in `{filename}`, press `yes` to confirm: "
            command = f"git checkout -- {filename}"
        elif "stage" in item:
            prompt = f"You will remote all changes in `{filename}`, press `yes` to confirm: "
            self.git_unstage(filename)
            command = f"git checkout -- {filename}"
        if input_no_throw(prompt) == "yes": 
            FileSystem().command(command)
            GPW.hide()
            self.on_space() # to save the changes
            self.mult.reset(*self.git_stage_files())
            self.redraw()

    def start_edit(self):
        number = self.cur_cursor_line()
        if number < 1: return True
        file = self.mult.items[number-1][10:]
        GPW.hide()
        self.close()
        FileSystem().edit(file)

    def git_show(self, item):
        if "untrace" in item: 
            print ("Can't show untrace file.")
            return
        if "unstage" in item: 
            lines = FileSystem().eval(f"git diff -- {item[10:]}")
        elif "stage" in item: 
            lines = FileSystem().eval(f"git diff --cached {item[10:]}")
        self.preview(item[10:], lines)
        
    def preview(self, file, lines):
        position = { 'zindex': 1000, }
        GPW.set_showable([
            PreviewWindow.ContentItem(file, lines, "magit", 1, position)
        ])
        GPW.trigger()

    def on_exit(self): 
        GPW.hide()
        self.on_space()
        

@vim_register(command="GitCommit")
def StartGitCommit(args):
    commit = GitCommitter()
    commit.create()
    commit.show()
