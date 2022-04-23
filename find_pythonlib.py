import glob
files = glob.glob('/usr/lib/python3.8/config-3.8*')
if len(files) == 0:
    print("[Error]:" + "Not Found libpython3.8.")
else: 
    print(files[0] + '/')
