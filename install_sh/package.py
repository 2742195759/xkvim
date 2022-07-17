import glob
import os
os.system("mkdir lib")

"""
package a compiled program into distribute program.

```
mkdir dist
cd dist
cp ../vim vim
python3 package.py --name vim
```
"""

def parameter_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Support Args:")
    parser.add_argument("--name", type=str, help="file-path")
    return parser.parse_args()
args = parameter_parser()

to_copy = []
to_copy.append(args.name)
copyed = []

def copy_dep(name):
    import subprocess
    cmd = ("ldd %s"%name)
    child = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
    for line in child.stdout.readlines(): 
        line = line.strip()
        if "=>" in line: 
            file = line.split("=>")[1].strip().split(" ")[0].strip()
        else: 
            file = line.split(" ")[0].strip()
        os.system(f"cp {file} ./lib")

while True:
    if len(copyed) == len(to_copy) + 1: # name is not in the lib/
        break
    for i in to_copy:
        if i not in copyed:
            copy_dep(i)
            copyed.append(i)
            to_copy = glob.glob('lib/*')

import pdb
pdb.set_trace() 
os.system(f"patchelf --set-rpath ./lib {args.name}")
interpreter = glob.glob("./lib/ld-linux-x86-64*")
assert len(interpreter)>0, "don't have ld.so."
os.system(f"patchelf --set-interpreter './{interpreter[0]}' {args.name}")
