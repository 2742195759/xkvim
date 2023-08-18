import re
import os
import sys

#keyword = "526385152"

pattern_int = r"[0-9]+"
pattern_hex = r"0x[0-9a-f]+"

leak_set = {}
tmp_var = {}

release_size = 0

def process(line):
    global release_size
    if "Free" in line: 
        m = re.search(f"Free ({pattern_int}) bytes, ptr = ({pattern_hex})", line)
        if m:
            size, ptr = m.group(1), m.group(2)
            if ptr not in leak_set: 
                release_size += int(size)
                #assert ptr in leak_set, f"{ptr} is not found."
            else:
                tmp_var[ptr] = 1
                del leak_set[ptr]
    if "Alloc" in line: 
        m = re.search(f"Alloc ({pattern_int}) bytes, ptr = ({pattern_hex})", line)
        if m:
            size, ptr = m.group(1), m.group(2)
            leak_set[ptr] = size

start = False
collect = True
for idx, line in enumerate(sys.stdin):
    line = line.strip()
    if "New Step" in line:
        collect = False
        if start == False: start = True
        else: 
            break
    if start: 
        process(line)

leak_size = 0

print ("Leakage Var is :")
for key, value in leak_set.items():
    if key in tmp_var: 
        leak_size += int(value)
        print ("\t", key, value)

print ("Parameter Var is: ")
for key, value in leak_set.items():
    if key not in tmp_var: 
        leak_size += int(value)
        print ("\t", key, value)

print ("Leakage Size:", leak_size)
print ("Release Size:", release_size)

### TODO: conclude and product a docs.
### VLOG + Tools -> locate Problems  .
