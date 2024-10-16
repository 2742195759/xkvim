from .buf_app import WidgetBufferWithInputs, WidgetList, TextWidget, SimpleInput, CommandList, BufferHistory
from .func_register import vim_register, get_all_action
from .vim_utils import SetVimRegister, input_no_throw, dequote, special_path_eval
from .remote_fs import FileSystem
from .windows import MessageWindow
import vim
import os

#"tnoremap <M-a> <Cmd>TerminalAbbre<cr>

code_action_dict = {
    "abbre             |  缩写插入模式  |": "TerminalAbbre",
    "git committer     |  开始git提交   |": "GitCommit",
    "file tree         |  远程的文件树  |": "FileTree",
    "insert filepath   |  插入文件路径  |": "InsertFilePath",
    "tag list          |  展示代码结构  |": "TagList",
    "file finder       |  文件模糊查找  |": "FF",
    "buffer finder     | Buffer模糊查找 |": "B",
    "search keyword    |   关键字查找   |": "UniverseSearchWithPath",
    "google            |    谷歌查找    |": "GoogleUI",
    "paddle doc        |   Paddle文档   |": "PdocUI",
    "baidu_fanyi       |    百度翻译    |": "Fanyi",
    "yiyan             |  百度文心一言  |": "YiyanTrigger", 
    "preview window    |   QuickPeek    |": "QuickPeek",
    "create tmp file   | 创建新临时文件 |": "@CreateTmp",
    "change directory  |    更换目录    |": "@ChangeDirectory",
    "set remote        |  更换远程机器  |": "@SetRemote",
    "clean swp         | 删除掉swap文件 |": "CleanSwaps",
    "restart           | 重新启动服务   |": "RestartAll",
    "yiyan code accept |一言接受代码建议|": "YiyanCodeAccept",
    "yiyan code        |一言接受生成代码|": "@YiyanCode",
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
        local=1,
    )
    code_action = CommandList("    [ CodeAction ]    ", keys, vals, options, code_action_history)
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
    FileSystem().edit_temp_file(args[0])

@vim_register(command="ChangeDirectory", with_args=True, command_completer="customlist,RemoteFileCommandComplete")
def ChangeDirectoryCommand(args):
    """ 
    `ChangeDirectoryCommand <new-directory>`: change search directory and filefinder directory.
    >>> ChangeDirectoryCommand /home/data/xkvim/
    >>> ChangeDirectoryCommand /home/data/Paddle/
    更换当前的目录，包含两者：search directory 和 filefinder directory
    但是不包含NERDTree 和 vim 的根目录.
    """
    from .rpc import remote_project
    if len(args) == 0: 
        directory_path = remote_project.origin_directory
    else: 
        if args[0] == '-': 
            directory_path = remote_project.last_directory
        else: 
            directory_path = args[0]
            directory_path = dequote(directory_path, special_path_eval)
    print (f"Changing directory: {directory_path}")
    vim.command(f"FR {directory_path}")
    vim.command(f"ChangeSearchDirectory {directory_path}")
    if remote_project: remote_project.change_directory(directory_path)
    FileSystem().remount()

last_searched_directory = ""
@vim_register(command="UniverseSearchWithPath")
def UniverserSearchWithPath(args):
    if len(args) == 0: 
        global last_searched_directory 
        cwd = input_no_throw("SearchCwd: ", f"{last_searched_directory}", "customlist,RemoteFileCommandComplete")
    else:
        cwd = str(args[0])
    if cwd is None: return
    if cwd == "": cwd = FileSystem().getcwd() 
    last_searched_directory = cwd
    MessageWindow().set_markdowns([f'Search path : {cwd}'])
    MessageWindow().show()
    try:
        input_text = input_no_throw(f"US>>>")
        if input_text is None: return 
        from Xiongkun import UniverseSearchEngine
        UniverseSearchEngine.singleton().search(input_text, cwd, [0,0,0,1])
        UniverseSearchEngine.singleton().render()
    finally:
        MessageWindow().hide()
    
@vim_register(command="CleanSwaps")
def CleanSwapFiles(args):
    cwd = FileSystem().getcwd()
    FileSystem().eval(f"find {cwd} -name '.*.swp' | xargs rm ")

def send_keys(bufnr, keys):
    vim.eval(f"term_sendkeys({bufnr}, \"{keys}\")")

vim.command(""" 
inoremap <silent> <m-a> <cmd>CodeAction<cr>
""")
vim.command(""" 
tnoremap <silent> <m-a> <cmd>CodeAction<cr>
""")
vim.command(""" 
tnoremap <silent> <m-.> <cmd>CodeActionLast<cr>
""")
vim.command(""" 
inoremap <silent> <m-.> <cmd>CodeActionLast<cr>
""")

@vim_register(command="RestartAll")
def RestartAllServer(args):
    vim.command("call UltiSnips#RefreshSnippets()")
