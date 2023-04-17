from .buf_app import WidgetBufferWithInputs, WidgetList, TextWidget, SimpleInput, CommandList
from .func_register import vim_register
from .vim_utils import SetVimRegister
import vim

code_action_dict = {
    "file finder       |文件模糊查找|": "FF",
    "universe find     | 关键字查找 |": "call UniverseSearch()",
    "google            |  谷歌查找  |": "Google",
    "baidu_fanyi       |  百度翻译  |": "Fanyi",
    "yiyan             |百度文心一言|": "YiyanTrigger", 
    "preview window    |  QuickPeek |": "QuickPeek",
}

@vim_register(command="CodeAction", keymap="<m-a>")
def CodeAction(args):
    keys, vals = [], []
    for key, val in code_action_dict.items():
        keys.append(key)
        vals.append(val)
    code_action = CommandList("[ CodeAction ]", keys, vals)
    code_action.create()
    code_action.show()

vim.command(""" 
inoremap <silent> <m-a> <cmd>CodeAction<cr>
""")
