import os.path as osp

def parameter_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Support Args:")
    parser.add_argument("--name",                 type=str,   default="./data/Amazon_Instant_Video/",  help="data path")
    parser.add_argument("--cmd",                  type=str,   default="./data/Amazon_Instant_Video/",  help="data path")
    return parser.parse_args()

args = parameter_parser()
import json
import requests
headers = {"Content-Type":"application/json"}
headers['Type'] = 'snd'
headers['Name'] = args.name
ret = requests.post("http://10.255.125.22:8084", data=json.dumps({'cmd':args.cmd, 'password':'807377414'}), headers=headers)
print (ret.status_code, ret.reason)
