import os
import sys
import json
import time
from log import log

def GetConfigByKey(key, directory='./'):
    import yaml  
    # 打开 YAML 文件  
    path = os.path.join(directory, ".vim_config.yaml")
    #log(f"[SearchConfig] config_file = {path}")
    if not os.path.exists(path): 
        #log(f"[SearchConfig] not exist.")
        return []
    with open(path, 'r') as f:  
        # 读取文件内容  
        data = yaml.safe_load(f)  
    # 输出解析结果  
    if key not in data: return []
    return data[key]


def GetSearchConfig(directory):
    config_lines = GetConfigByKey("search_config", directory)
    excludes_dir = []
    excludes_file = []
    for line in config_lines: 
        if line.startswith("--exclude-dir="):
            excludes_dir.append(line.split("=")[1].strip()[1:-1])
        elif line.startswith("--exclude="): 
            excludes_file.append(line.split("=")[1].strip()[1:-1])
    #print("[SearchConfig]", excludes_dir + excludes_file)
    return excludes_dir, excludes_file


def GetSearchFindArgs(excludes):
    dirs, files = excludes
    find_cmd = []
    for exclude in dirs: 
        find_cmd.append(" ".join(["-not", "-path", f"\"*{exclude}\""]))
    for exclude in files: 
        find_cmd.append(" ".join(["-not", "-name", f"\"*{exclude}\""]))
    #log("[FindCmd]: ", find_cmd)
    find_cmd = " -a ".join(find_cmd)
    return find_cmd


def GetSearchFiles(directory):
    base_cmd = f"find {directory} "
    excludes = GetSearchConfig(directory)
    find_args = GetSearchFindArgs(excludes)
    find_cmd = base_cmd + find_args
    return GetSearchFilesFromCommand(find_cmd)


def GetSearchFilesFromCommand(find_cmd):
    import subprocess
    child = subprocess.Popen(f"{find_cmd}", shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
    #log ("[FileFinder]:", find_cmd)
    files = []
    for line in child.stdout.readlines():
        line = line.strip()
        if line and os.path.isfile(line):
            files.append(line)
    return files


def GetSearchGrepArgs(excludes):
    dirs, files = excludes
    grep_cmd = []
    for exclude in dirs: 
        exclude = exclude.replace("/*", "")
        exclude = exclude.replace("/", "")
        grep_cmd.append(f' --exclude-dir="{exclude}" ')
    for exclude in files: 
        grep_cmd.append(f' --exclude="{exclude}" ')
    #log("[FindCmd]: ", grep_cmd)
    return grep_cmd

def escape(command, chars="'\\\""):
    l = []
    for c in command:
        if c in chars: l.append("\\" + c)
        else : l.append(c)
    return "".join(l)
