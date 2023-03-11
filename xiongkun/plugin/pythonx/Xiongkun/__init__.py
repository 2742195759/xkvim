from .gitcomment import *
from .vim_parser import *
from .func_register import echo
from .vim_utils import *
from .ijump import *
from .clangd_client import *
from .windows import *
from .multiprocess_utils import *
from .multi_location_ops import *
from .indexer import *
from .converse_plugin import *
from .insert_keymap import *
from .fold_plugin import *
from .buf_app import *
from .quick_note import *
from .remote_terminal import *
from .log_analysis_plugin import *
from .traceback import *
from .quick_jump import QuickJump, BufferJump, WindowJump, GlobalJump
from .quick_jump import State as jump_state
from .log import OpenLog
from .paddle import *
from .rpc import *

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

@vim_register(command="Test")
def Test(args):
    assert toCapitalize("lgamma_grad") == "LgammaGrad"
    assert toCapitalize("lgamma") == "Lgamma"
    print("implement what you want to test.")

@vim_register(command="Yaml", with_args=True)
def YamlGen(args):
    from os import path as osp
    op_name = args[0]
    if len(args) == 2 : backward = args[1]
    prefix = "/home/data/Paddle4/Paddle/"
    EditFileWithPath(osp.join(prefix, 'python/paddle/utils/code_gen/api.yaml'), "tabe")
    EditFileWithPath(osp.join(prefix, 'python/paddle/utils/code_gen/backward.yaml'), "vne")
    yaml_string = vim.eval('system("python3 /home/data/web/scripts/yaml_generator.py --op_name=%s --backward=%s")' % (op_name, backward))
    print (yaml_string)
    SetVimRegister("y", yaml_string)
    EditFileWithPath(osp.join(prefix, 'paddle/phi/kernels/%s_kernel.h' % op_name), "tabe")
    EditFileWithPath(osp.join(prefix, 'paddle/fluid/operators/%s_op.cc' % op_name), "tabe")
    SearchToString("InferMeta")
    EditFileWithPath(osp.join(prefix, 'python/paddle/fluid/tests/unittests/test_%s_op.py' % op_name), "tabe")
    SearchToString("self.op_type")  # for write python_api
    SetVimRegister("z", "")
    EditFileWithPath(osp.join(prefix, 'python/xktmp.py'), "tabe")
    ClearCurrent()

@vim_register(command="YamlC", with_args=True)
def YamlGenCursor(args):
    from os import path as ops
    op_name = args[0]
    filename = CurrentEditFile(True)
    start = GetCursorXY()[0] - 1
    yaml_string = vim.eval('system("python3 /home/data/web/scripts/yaml_generator.py --op_name=%s --file=%s --start=%d")' % (op_name, filename, start))
    SetVimRegister("y", yaml_string)

@vim_register(command="YamlR")
def YamlReplace(args):
    vim.command('g/self.check_grad/execute "normal" "f(%i, check_eager=True"')
    vim.command('g/self.check_output/execute "normal" "f(%i, check_eager=True"')

@vim_register(command="FN")
def CopyFileName(args):
    filename = vim_utils.CurrentEditFile()
    vim_utils.SetVimRegister('"', filename)
    cmd = "/bin/cp ../%s ./%s" % (filename, filename)
    os.system("echo %s >> /home/data/web/scripts/copy_file.sh" % cmd)

@vim_register(command="SearchConfig")
def EditSearchConfig(args):
    vim.command("tabe search_config")
    if EmptyBuffer(): 
        vim.command("read ~/xkvim/search_config")
        vim.command("normal 0d_")

