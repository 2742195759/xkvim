from .gitcomment import *
from .vim_parser import *
from .func_register import echo
from .vim_utils import *
from .ijump import *
from .clangd_client import *
from .windows import *
from .multiprocess_utils import *
from .multi_location_ops import *
#from .indexer import *
from .converse_plugin import *
from .insert_keymap import *
from .fold_plugin import *
from .buf_app import *
from .quick_note import *
from .remote_terminal import *
from .log_analysis_plugin import *
from .traceback import *
from .quick_jump import *
from .quick_edit import *
from .log import OpenLog
from .paddle import *
from .rpc import *
from .yiyan import *
from .buf_app_translate import *
from .buf_app_code_action import *
from .buf_app_filetree import *
from .buf_app_git_committer import *
from .buf_app_code_preview import *
from .command_doc_popup import *
from .filetype_plugin import *
from .remote_fs import *
from .haskell import *
from .insert_complete import *
from .haskell_rpc import *

pro = None; 

@vim_register( command="NN")
def Next(args):
    pro.next()

@vim_register( command="HH")
def Help(args):
    print (
"""
HH      ===>   help page.
FF      ===>   File Finder simulate CtrlP with faster speed. hotkey: <C-P><C-P>.
NN      ===>   next stage.
Impl    ===>   create_impl_file for cpu / gpu reuse.
Helper  ===>   create_helper for cpu / gpu reuse.
Start   ===>   start project and goto stage1.  [deleted]
FN      ===>   Copy File Name of current file into @" and copy_file.sh.
Compile ===>   Get clangd diags. 10x speed up for Paddle Compile and Modifty.
Make    ===>   Paddle make and cfile the error.
<F4>    ===>   Reflesh the screen.
<F5>    ===>   File tree.
<F6>    ===>   Toggle tag list.
<F9>    ===>   Restart the UltiSnippet and YCM Server.
Latex   ===>   compile the current edit latex file, and popup in your Mac. Need WebServerCenter.
IFuzzy|IFind ===> Fuzzy Match By Clangd Indexer.  [ useful for code complete and preview. ]
ProfileProject  ===> ProfileProeject ./ FLAGS_new_einsum=1 python3.7 main.py.
Reload  ===>   reload Xiongkun python plugin, make all the changes work.
Traceback ===> Traceback a stack output, current only support python language.
<TODO>  ===>   Code Complete by clangd. clangd is slower but more stable, more accurary than YCM. Use my own compile tools.
""")

@vim_register( command="HI")
def HelpInsert(args):
    print (
"""
Insert Key Map:
<ctrl>( : insert ( CURRENT_LINE )
<ctrl>{ : insert { CURRENT_LINE }
<ctrl>[ : insert [ CURRENT_LINE ]
""")

@vim_register(command="Start")
def Start(args):
    global pro
    pro = pten_transfer.Project()
    pro.start_project()
    pro.next()

@vim_register(command="Impl")
def Impl(args):
    global pro
    pro.create_impl_file()

@vim_register(command="Helper")
def Helper(args):
    global pro
    pro.create_helper_file()

@vim_register(command="VimConfig")
def EditSearchConfig(args):
    path = ".vim_config.yaml"
    if not FileSystem().exists(path): 
        FileSystem().create_node(path)
    FileSystem().edit(path, True)
    if EmptyBuffer(): 
        vim.command("read ~/xkvim/vim_config.yaml")

@vim_register(command="YankLine")
def YankLine(args):
    """ yank a paramgraph as a line: remove the \n beween them. 
        add the yanked line to the register @"
    """
    word = vim_utils.GetVisualWords()
    word = word.replace("\n", "")
    vim_utils.SetVimRegister('"', word)
    return word

@vim_register(command="SetRPCProject", with_args=True, command_completer="file")
def SetRPCServer(args):
    from .rpc import set_remote_project
    from .clangd_client import set_remote_lsp
    set_remote_project(args[0])
    FileSystem().remount()
    vim.command("ChangeDirectory")
    set_remote_lsp(args[0])
    vim.command("wincmd o")

@vim_register(command="Reconnect")
def RPCServerReconnect(args):
    XKVIM_reflesh_screen([])
    from .rpc import remote_project
    # reconnect the rpc server
    SetRPCServer([remote_project.config_file])

@vim_register(keymap="<c-l>")
def XKVIM_reflesh_screen(args):
    MessageWindow().hide()
    InsertWindow().close()
    vim.eval('feedkeys("\\<Cmd>call system(\\"resize\\")\\<cr>\\<Cmd>redraw!\\<cr>\\<Cmd>syntax sync fromstart\\<cr>")')
    vim.command('set mouse=')
    GlobalPreviewWindow.hide()
    LSPDiagMessageWindow().hide()
