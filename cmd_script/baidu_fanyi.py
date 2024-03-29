import hashlib
import requests
import os

def parameter_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Support Args:")
    parser.add_argument("--query",                 type=str,  help="please insert your input query.")
    return parser.parse_args()

args = parameter_parser()
if 'fanyi_password' not in os.environ: 
    print ("找不到环境变量：$fanyi_password")
    exit(0)
pwd = os.environ['fanyi_password']
app_id = "20220715001273779"
salt = "123123123"
query = args.query
query = query.strip("# ")
if query.isascii():
    fr = "en"
    to = "zh"
else: 
    fr = "zh"
    to = "en"
sign = hashlib.md5((app_id + query + salt + pwd).encode("utf=8")).hexdigest()
url = f"http://api.fanyi.baidu.com/api/trans/vip/translate?q={query}&from={fr}&to={to}&appid={app_id}&salt={salt}&sign={sign}"
out = requests.get(url)
if "trans_result" in out.json(): 
    print(out.json()['trans_result'][0]['dst'])
else: 
    print(out.json())
