from .buf_app import Buffer
from .func_register import vim_register, get_docs
from .vim_utils import Singleton, dict2str, TotalWidthHeight, commands
import vim
from .log import log

# main.vim: DocPreviewGroup

@Singleton
class DocPreviewBuffer(Buffer):
    def __init__(self):
        col, line = TotalWidthHeight()
        self.win_options = {
            'maxwidth': 80,
            'minwidth': 50,
            'maxheight': 10,
            'filter': None,
            'pos': 'botleft',
            'title': ' DocPreview ',
            'line': line - 1,
            'col': 1,
        }
        super().__init__("doc-preview", None, self.win_options)
        self.markdown_doc = "EmptyBuffer"
        self.dirty = False
        self.create()

    def set_markdown_doc(self, markdown_doc):
        if self.markdown_doc != markdown_doc and markdown_doc != "No Docs.":
            self.dirty = True
        self.markdown_doc = markdown_doc
        self.onredraw()
        return self

    def _set_syntax(self):
        self.execute(f'set syntax=markdown')

    def auto_skip_indent(self, lines):
        source_code = lines.split('\n')
        source_code = [line for line in source_code if line.strip()]
        indent = len(source_code[0]) - len(source_code[0].lstrip())
        source_code = [line[indent:] for line in source_code]
        return source_code

    def onredraw(self):
        self._clear()
        self._put_strings(
            self.auto_skip_indent(self.markdown_doc)
        )

    def show(self):
        super().show()
        if self.dirty: 
            vim.command("redraw")
        self.dirty = False
        config = dict2str(self.win_options)
        vim.eval(f"popup_move({self.wid}, {config})")
            

    def set_command_doc(self):
        vim.command("set eventignore=all")
        commandline = vim.eval("getcmdline()")
        log(f"[DocPreview] {commandline}")
        command = commandline
        if ' ' in commandline:
            command = commandline.split(' ')[0]
        log(f"[DocPreview] docs: {get_docs(command)}")
        self.set_markdown_doc(get_docs(command))
        vim.command("set eventignore=")
        return self

    def is_dirty(self):
        self.dirty

@vim_register(command="TestDocPreview", with_args=True)
def TestDocPreview(args):
    """
    ## Overview
    *test case*: Test the DocPreview Window.
    """
    markdown = """
        # Usage
        SetRemote REMOTE_NAME
        # remote name
        pc | mac
    """
    ff = DocPreviewBuffer()
    if "".join(args): 
        ff.set_markdown_doc(" ".join(args))
    ff.show()

@vim_register(command="DocPreviewUpdate")
def DocPreviewUpdate(args):
    """
    ## Overview
    *show* the CommandDocPreview window for promote.
    """
    DocPreviewBuffer().set_command_doc().show()

@vim_register(command="DocPreviewHide")
def DocPreviewHide(args):
    """
    ## Overview
    *hide* the CommandDocPreview window for promote.
    """
    DocPreviewBuffer().set_command_doc().hide()

### AutoCmd for DocPreview
commands("""
augroup DocPreviewGroup
    autocmd!
    autocmd CmdlineChanged * DocPreviewUpdate
    autocmd CmdlineLeave * DocPreviewHide
augroup END
""")
