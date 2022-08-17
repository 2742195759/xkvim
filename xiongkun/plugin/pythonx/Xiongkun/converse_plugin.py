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

def open_url_on_mac(url):
    cmd = """open "%s" """ % url
    ExecuteCommand("mac", cmd, silent=True)
    
def ExecuteCommand(name, cmd, silent=True):
    import json
    import requests
    headers = {"Content-Type":"application/json"}
    headers['Type'] = 'snd'
    headers['Name'] = name
    ret = requests.post("http://10.255.125.22:8084", data=json.dumps({"cmd": cmd, 'password':'807377414'}), headers=headers)
    if not silent: 
        print (ret.status_code, ret.reason)
        print (ret.text)

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
    os.system(f"~/xkvim/cmd_script/remove.sh profile")
    os.system(f"~/xkvim/cmd_script/send_profile_task.sh {abs_path} \"{cmd}\"")
    os.system(f"python3 ~/xkvim/cmd_script/converse_execute.py --name mac --cmd " + f"\"cd ~/my_report/ && curl http://10.255.125.22:8082/my_report.qdrep --output {random_name} && open ./{random_name}\"")

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
