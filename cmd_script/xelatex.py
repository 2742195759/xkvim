import os.path as osp

def parameter_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Support Args:")
    parser.add_argument("--file",                 type=str,   default="./data/Amazon_Instant_Video/",  help="data path")
    return parser.parse_args()

args = parameter_parser()

def send(name="", cmd="", password=""):
    import json
    import requests
    headers = {"Content-Type":"application/json"}
    headers['Type'] = 'snd'
    headers['Name'] = name
    return (requests.post("http://10.255.125.22:8084", data=json.dumps({'cmd':cmd, 'password':password}), headers=headers))

def xelatex_make(filepath):
    abspath = osp.abspath(args.file)
    dire = osp.dirname(abspath)
    path = osp.basename(abspath)
    pdfpath = path.split('.')[0] + '.pdf'
    rsp = send("xelatex", f"cd {dire} && xelatex --halt-on-error {path} 2>&1", "807377414")
    print (rsp.reason)
    print (rsp.text)
    send("mac", f"open /Users/xiongkun03/latex/{pdfpath}", "807377414")

if __name__ == "__main__":
    xelatex_make(args.file)
