import os.path as osp

def parameter_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Support Args:")
    parser.add_argument("--file",                 type=str,   default="./data/Amazon_Instant_Video/",  help="data path")
    return parser.parse_args()

args = parameter_parser()

def send(cmd="", password=""):
    import json
    import requests
    headers = {"Content-Type":"application/json"}
    return requests.post("http://192.168.1.6:8000", data=json.dumps({'cmd':cmd, 'password':password}), headers=headers)

def xelatex_make(filepath):
    abspath = osp.abspath(args.file)
    dire = osp.dirname(abspath)
    path = osp.basename(abspath)
    send(f"cd {dire} && xelatex {path}", "807377414")

if __name__ == "__main__":
    xelatex_make(args.file)
