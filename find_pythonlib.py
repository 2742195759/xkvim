import glob
import platform
version = ".".join(platform.python_version().split('.')[0:2])
files = glob.glob(f'/usr/lib/python{version}/config-{version}*')
if len(files) == 0:
    print("[Error]:" + "Not Found libpython3.8.")
else: 
    print(files[0] + '/')
