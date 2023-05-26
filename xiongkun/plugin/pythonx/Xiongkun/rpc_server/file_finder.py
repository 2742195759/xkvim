import os
import sys
import json
import time
from decorator import *
from log import log
from functions import KillablePool
from fuzzy_list import FuzzyList


def GetConfigByKey(key, directory='./'):
    import yaml  
    # 打开 YAML 文件  
    path = os.path.join(directory, ".vim_config.yaml")
    log(f"[SearchConfig] config_file = {path}")
    if not os.path.exists(path): 
        log(f"[SearchConfig] not exist.")
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
    log ("[FileFinder]:", find_cmd)
    files = []
    for line in child.stdout.readlines():
        line = line.strip()
        if line and os.path.isfile(line):
            files.append(line)
    return files

class FileFinder:
    def __init__(self):
        self.root = None
        self.fuzzy = FuzzyList()
        pass

    def _get_files(self):
        return ['sdfsdf', 'sdfsd']

    @server_function
    def set_root(self, rootpath):
        self.root = rootpath
        self.files = self._get_files()
        self.files = GetSearchFiles(self.root)
        # TODO: find files and reset it.
        self.fuzzy.set_items(-1, "filefinder", self.files)
        return self.files[:17]

    # transfer only
    def search(self, id, name, search_text):
        return self.fuzzy.search(id, 'filefinder', search_text)

filefinder = FileFinder()

if __name__ == "__main__":
    test_main()
