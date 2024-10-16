import sys
import os
def parameter_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Support Args:")

    parser.add_argument("--t",                 type=str,   default=None,  help="data path")
    return parser.parse_args()

def swap_column(lines, delim="&", end="//", transpose=None): 
    if len(lines) <= 0: return ""
    ret = []
    ncolumns = len(lines[0].split("\\\\")[0].split(delim))
    if transpose == None: 
        transpose = range(ncolumns)
    for line in lines:
        columns = line.split("\\\\")[0].split(delim)
        assert len(columns) == ncolumns, "Column is not the same."
        new_columns = []
        for t in transpose:
            new_columns.append(columns[t])
        ret.append("&".join(new_columns) + " \\\\")
    return "\n".join(ret)

if __name__ == "__main__":
    args = parameter_parser()
    trans = args.t.split(",")
    trans = [ int(t) for t in trans ]
    lines = sys.stdin.readlines()
    output = swap_column(lines, transpose=trans)
    print(output)
