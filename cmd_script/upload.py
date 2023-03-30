import sys
import requests
from requests_toolbelt import *
def parameter_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Support Args:")
    parser.add_argument("--url",                 type=str,   default="http://10.255.125.22:8082/",  help="data path")
    parser.add_argument("--file",                 type=str,   default=None,  help="data path")
    parser.add_argument("--rename",                 type=str,   default=None,  help="data path")
    return parser.parse_args()

args = parameter_parser()
URL = args.url
file = args.file
if args.rename is None: filename = file.split("/")[-1]
else: filename = args.rename

m = MultipartEncoder(
    {'file': (filename, open(file, 'rb'),
                     'application/octet-stream')})

headers = {
    "Content-Type": m.content_type,
    "referer": URL,
    "charset":"UTF-8",
}
re = requests.post(URL, data=m, headers=headers)
if re.status_code != 200:
    print(re)
    exit (1)
