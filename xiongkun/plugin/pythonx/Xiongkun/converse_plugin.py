import vim
import subprocess
import os
from os import path as osp
from . import vim_utils
from .func_register import *
import random
import threading
import json
from contextlib import contextmanager
import time
import os.path as osp
from .log import log, log_google
from urllib.parse import quote
import shlex

@vim_utils.Singleton
class RemoteConfig:
    def __init__(self):
        self.default_remote = "mac"
        self.remote_name = self.default_remote
        pass

    def set_remote(self, remote_name):
        self.remote_name = remote_name

    def get_remote(self):
        assert self.remote_name is not None, "Please set remote first."
        return self.remote_name

def open_url_on_mac(url):
    cmd = """open "%s" """ % url
    ExecuteCommand("mac", cmd, silent=True)
    
def ExecuteCommand(name, cmd, silent=True):
    import json
    import requests
    headers = {"Content-Type":"application/json"}
    headers['Type'] = 'snd'
    headers['Name'] = name
    try:
        ret = requests.post("http://10.255.125.22:8084", data=json.dumps({"cmd": cmd, 'password':'807377414'}), headers=headers, timeout=3)
    except Exception as e:
        print(f"Failed to connect to server. {e}")
        return 
    if not silent or ret.status_code != 200:
        print (f"Return Code is {ret.status_code}, please check the server.")
        print (f"{ret.reason}")
    if not silent: 
        print (ret.text)

@vim_register(command="SetRemote", with_args=True)
def SetRemote(args):
    RemoteConfig().set_remote(args[0])
    print(f"set the remote name to -> {args[0]}")

@vim_register(command="Google", with_args=True)
def Google(args):
    from os import path as ops
    text = " ".join(args)
    if not text: 
        text = vim_utils.GetCurrentWord()
    if text: log_google(text)
    url_text = quote(text)
    """ 
    MacOs: open "http://" can open a http website in default browser.
    """
    cmd = """open "https://www.google.com.hk/search?q=%s" """ % url_text
    log(cmd)
    ExecuteCommand("mac", cmd, silent=True)

@vim_register(command="Paper", with_args=True)
def RandomReadPaper(args):
    papers = [
        'Selected the Conference:',
        '1. 计算机自动化: Automated Software Engineering', 
        '2. 离散算法: TALG', 
        '3. CCF 排名',
    ]
    link = [
        'place_holder',
        'https://www.springer.com/journal/10515', 
        'https://dl.acm.org/toc/talg/2022/18/1', 
        'https://www.ccf.org.cn/Academic_Evaluation/TCS/',
    ]
    lis = vim_utils.VimVariable(papers)
    selected = int(vim.eval(f"inputlist({lis.name()})"))
    open_url_on_mac(link[selected])
    #open_url_on_mac("https://www.ccf.org.cn/Academic_Evaluation/TCS/")
    #"http://acm-stoc.org/stoc2021/accepted-papers.html"

@vim_register(command="ProfileProject", with_args=True)
def ProfileProject(args):
    """ --args0: project root path, directory
        --args1: project start command
    """
    assert len(args) >= 2, "Must have 2 arguments:  <ROOT> <CMD>"
    assert osp.isdir(args[0])
    abs_path = osp.abspath(args[0])
    dir_name = osp.basename(abs_path)
    cmd = f"cd {dir_name} && " + " ".join(args[1:])
    print(dir_name, abs_path, cmd)
    random_name = "tmp_" + vim.eval("rand()") + ".qdrep"
    os.system(f"~/xkvim/cmd_script/send_profile_task.sh {abs_path} \"{cmd}\"")
    from .remote_terminal import TerminalStart, LoadConfig, send_keys
    config = LoadConfig()
    bufnr = TerminalStart(config.profile['ssh_url'], config.profile['ssh_passwd'], config.profile['docker_cmd'], "/home/ssd3/xiongkun")
    send_keys(bufnr, f"/home/ssd3/xiongkun/prepare_profile.sh\n\r")
    send_keys(bufnr, f"cd /home/ssd3/xiongkun/profile\n\r")

@vim_register(command="Make")
def PaddleMake(args):
    def send(cmd="", password=""):
        import json
        import requests
        headers = {"Content-Type":"application/json", "port": '1000'}
        return requests.post("http://10.255.129.13:10000", data=json.dumps({'cmd':cmd, 'password':password}), headers=headers)
    project_path = vim_utils.get_git_prefix(vim_utils.CurrentEditFile())
    build_path = os.path.join(project_path, "build/")
    error_file = os.path.join(build_path, "error.txt")
    vim_utils.Notification("Compiling...Please wait.")
    send(f"cd {build_path} && ./rebuild.sh >{error_file} 2>&1", "807377414")
    vim.command(f"cfile {error_file}")

def baidu_translate(sentence):
    import subprocess
    sentence = sentence.replace("\n", "")
    cmd = "python3 ~/xkvim/cmd_script/baidu_fanyi.py --query \"{sentence}\"".format(
        sentence = sentence,
    )
    child = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
    info = child.stdout.readline().strip()
    return info

def run_python_file(python_file, **kwargs):
    import subprocess
    args_str = []
    pre_command = ["source ~/.bashrc"]
    with open(python_file, "r") as fp :
        lines = fp.readlines()
        for line in lines:
            if line.startswith("#cmd:"):
                line = line.replace("#cmd:", "").strip()
                pre_command.append(line)
                
    for key, val in kwargs.items():
        args_str.append(f"--{key} {val}")
    args_str = " ".join(args_str)
    pre_command.append("python3")
    command_str = "&&".join(pre_command)
    cmd = f"bash -c '{command_str} {python_file} {args_str}'"
    log(f"Start run `{cmd}`")
    child = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    error = "".join(child.stderr.readlines()).strip()
    info = "".join(child.stdout.readlines()).strip()
    if error: 
        print("Error occur:\n", error)
        return ""
    return info

@vim_register(command="Trans")
def TranslateAndReplace(args):
    """ translate and replace the current visual highlight sentence.
    """
    word = vim_utils.GetVisualWords()
    info = baidu_translate(word)
    vim_utils.SetVisualWords(info)

@vim_register(keymap="K")
def Translate(args):
    word = vim_utils.GetCurrentWord()
    info = baidu_translate(word)
    vim.command("echom '百度翻译结果：'")
    print(info)

@vim_register_visual(keymap="K")
def VisualTranslate(args):
    """ `< and `>
    """
    text = vim_utils.GetVisualWords()
    info = baidu_translate(text)
    vim.command("echom '百度翻译结果：'")
    print(info)

@vim_register(command="Gast")
def GastDump(args):
    """ `< and `>
    """
    file = vim_utils.WriteVisualIntoTempfile()
    info = run_python_file("~/xkvim/cmd_script/dump_gast.py", file=file)
    print(info)

@vim_register(command="Run", keymap="<F9>")
def RunCurrentFile(args):
    """ Dump a function's bytecode into screen.
    """
    tmp_file = vim_utils.tempfile()
    vim.command(f"silent! w {tmp_file}")
    info = run_python_file(tmp_file)
    print (info)

@vim_register(command="Copyfile")
def PaddleCopyfile(args):
    """ In paddlepaddle, we call /home/data/web/scripts/copy_file.sh under each build* directory.
    """
    import glob
    import os
    for d in glob.glob("./build*"): 
        d = os.path.abspath(d)
        os.system(f"cd {d} && /home/data/web/scripts/copy_file.sh")
    print ("You paddlepaddle is updated.")

@vim_register(command="Pdoc", with_args=True)
def PaddleDocumentFile(args):
    """ In paddlepaddle, search the offical docuement and show the api usage.
    """
    text = " ".join(args)
    if not text: 
        text = vim_utils.GetCurrentWord()
    url_text = quote(text)
    url = f"https://www.paddlepaddle.org.cn/searchall?q={url_text}&language=zh&version=2.3"
    open_url_on_mac(url)

@vim_register(command="ShareCode")
def ShareCode(args):
    """ we share code into 0007 server.
    """
    word = vim_utils.GetVisualWords()
    open("/tmp/share.txt", "w").write(word)
    if vim_utils.system("python3 ~/xkvim/cmd_script/upload.py --file /tmp/share.txt")[0]: 
        print ("Your code is shared into http://10.255.125.22:8082/share.txt")

@vim_register(command="Share")
def ShareCodeToMac(args):
    """ we share code into 0007 server.
    """
    word = vim_utils.GetVisualWords()
    open("/tmp/share.txt", "w").write(word)
    if vim_utils.system("python3 ~/xkvim/cmd_script/upload.py --file /tmp/share.txt")[0]: 
        vim.command("ShareCodeCopyClipboard")
        

@vim_register(command="UploadFile", with_args=True)
def UploadFile(args):
    """ send a compressed file in local machine into 007 server and renamed to tmpfile.tar
    """
    if len(args) != 1: 
        print ("Usage: SendFile <local_file>|<local_dir>")
        return
    vim_utils.system(f"rm -rf /tmp/tmpfile && mkdir -p /tmp/tmpfile && cp -r {args[0]} /tmp/tmpfile")
    vim_utils.system("cd /tmp && tar -zcvf tmpfile.tar tmpfile")
    vim_utils.system("python3 ~/xkvim/cmd_script/upload.py --file /tmp/tmpfile.tar")

@vim_register(command="SendFile", with_args=True, command_completer="file")
def SendFile(args):
    """ 
    Usage: SendFile <local-file> | <local-dir> <remote-machine>
    upload file to 007 server and let remote machine open it.
    """
    UploadFile(args[:1])
    if os.path.isfile(args[0]):
        open_cmd = f"open /tmp/tmpfile/{os.path.basename(args[0])}"
    elif os.path.isdir(args[0]): 
        open_cmd = f"open /tmp/tmpfile"
    else: 
        print("Please inputs a valid direcotry or file path.")
    if len(args) <= 1:
        exe_machine = "mac"
    exe_machine = args[1]
    cmd = [
        "curl http://10.255.125.22:8082/tmpfile.tar --output /tmp/tmpfile.tar ",
        "cd /tmp && tar -zxvf tmpfile.tar && rm -rf tmpfile.tar" , 
        "cd /tmp/tmpfile ",
        open_cmd
    ]
    ExecuteCommand(exe_machine, "&&".join(cmd), silent=True)

@vim_register(command="ShareCodeCopyClipboard")
def CopyClipboard(args):
    cmd = "curl http://10.255.125.22:8082/share.txt | pbcopy "
    ExecuteCommand(RemoteConfig().get_remote(), cmd, silent=True)
    print("Shared!.")
