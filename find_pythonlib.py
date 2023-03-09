import glob
import platform
import glob
import platform
version = ".".join(platform.python_version().split('.')[0:2])
prefixs = ["/usr/lib",
           "/usr/local/lib",
           ]
files = []
for prefix in prefixs:
    files.extend(glob.glob(f'{prefix}/python{version}/config-{version}*'))
if len(files) == 0:
    print("[Error]:" + "Not Found Python.")
else:
    print(files[0] + '/')

