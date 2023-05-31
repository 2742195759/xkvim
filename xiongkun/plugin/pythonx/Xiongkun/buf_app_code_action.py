from .buf_app import WidgetBufferWithInputs, WidgetList, TextWidget, SimpleInput, CommandList, BufferHistory
from .func_register import vim_register, get_all_action
from .vim_utils import SetVimRegister
import vim
import os

code_action_dict = {
    "file tree         |  远程的文件树  |": "FileTree",
    "file finder       |  文件模糊查找  |": "FF",
    "universe find     |   关键字查找   |": "call UniverseSearch()",
    "google            |    谷歌查找    |": "GoogleUI",
    "paddle doc        |   Paddle文档   |": "PdocUI",
    "baidu_fanyi       |    百度翻译    |": "Fanyi",
    "yiyan             |  百度文心一言  |": "YiyanTrigger", 
    "yiyan login       |百度文心一言登录|": "YiyanLogin",
    "yiyan code        |文心一言代码生成|": "YiyanCode",
    "preview window    |   QuickPeek    |": "QuickPeek",
    "create tmp file   | 创建新临时文件 |": "@CreateTmp",
    "change directory  |    更换目录    |": "@ChangeDirectory",
    "set remote        |  更换远程机器  |": "@SetRemote",
    "clean swp         | 删除掉swap文件 |": "CleanSwaps",
}

vim.command(""" 
inoremap <silent> <m-a> <cmd>CodeAction<cr>
""")
vim.command(""" 
inoremap <silent> <m-.> <cmd>CodeActionLast<cr>
""")

code_action_history = BufferHistory("code_action_history")

@vim_register(command="CodeAction", keymap="<m-a>")
def CodeAction(args):
    keys, vals = [], []
    for key, val in code_action_dict.items():
        keys.append(key)
        vals.append(val)

    for command, tags, direct_do in get_all_action():
        keys.append(tags)
        if not direct_do: command = "@" + command
        vals.append(command)
        
    options = dict(
        minwidth=40,
        maxwidth=40,
        minheight=15,
        maxheight=15,
    )
    code_action = CommandList("[ CodeAction ]", keys, vals, options, code_action_history)
    code_action.create()
    code_action.show()

@vim_register(command="CodeActionLast", keymap="<m-.>")
def CodeActionLast(args):
    """ 
    Code Action Last Repeat.
    """
    if code_action_history.is_empty():
        return
    CommandList.run_command(code_action_history._value['cmd'])

@vim_register(command="YiyanLogin")
def YiyanDebug(args):
    vim.command("tab terminal")
    command = "/root/.local/share/pyppeteer/local-chromium/1000260/chrome-linux/chrome --disable-background-networking --disable-background-timer-throttling --disable-breakpad --disable-browser-side-navigation --disable-client-side-phishing-detection --disable-default-apps --disable-dev-shm-usage --disable-extensions --disable-features=site-per-process --disable-hang-monitor --disable-popup-blocking --disable-prompt-on-repost --disable-sync --disable-translate --metrics-recording-only --no-first-run --safebrowsing-disable-auto-update --password-store=basic --use-mock-keychain --remote-debugging-port=22 --remote-debugging-address=0.0.0.0 --user-data-dir=/root/xkvim/chrome-web/ --headless --hide-scrollbars --mute-audio about:blank --no-sandbox "
    bufnr = int(vim.eval("bufnr()"))
    send_keys(bufnr, command + '\n')

@vim_register(command="CreateTmp", with_args=True)
def CreateTmpfile(args):
    """
    `CreateTmp <sufix>`: 创建一个临时文件，后缀为 _<sufix>_
    >>> CreateTmp py # 创建一个临时的python文件
    >>> CreateTmp cc # 创建一个临时的c++文件
    """
    tmp_name = vim.eval("tempname()")
    vim.command(f"tabe {tmp_name}.{args[0]}")

@vim_register(command="ChangeDirectory", with_args=True, command_completer="file")
def ChangeDirectoryCommand(args):
    """ 
    `ChangeDirectoryCommand <new-directory>`: change search directory and filefinder directory.
    >>> ChangeDirectoryCommand /home/data/xkvim/
    >>> ChangeDirectoryCommand /home/data/Paddle/
    更换当前的目录，包含两者：search directory 和 filefinder directory
    但是不包含NERDTree 和 vim 的根目录.
    """
    assert len(args) == 1 and os.path.isdir(args[0]), "Please input a directory."
    directory_path = args[0]
    vim.command(f"FR {directory_path}")
    vim.command(f"ChangeSearchDirectory {args[0]}")

@vim_register(command="CleanSwaps")
def CleanSwapFiles(args):
    vim.eval('system("find ./ -name \'.*.swp\' | xargs rm ")')

def send_keys(bufnr, keys):
    vim.eval(f"term_sendkeys({bufnr}, \"{keys}\")")

vim.command(""" 
inoremap <silent> <m-a> <cmd>CodeAction<cr>
""")
