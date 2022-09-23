import sys
import argparse
import re
import pdb

def parameter_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Support Args:")
    parser.add_argument("-v", "--valid-expr",                type=str,   default="*",  help="when not match, the line will discard.")
    parser.add_argument("-e", "--extract-expr",              type=str,   default="loss {%f},", help="the extract expr for the loss")
    parser.add_argument("-r", "--reduction-expr",            type=str,   default="print", help="print | sum | mean")
    return parser.parse_args()

args = parameter_parser()

def is_valid(line, valid_expr):
    if valid_expr == "*" : return True
    if valid_expr in line: return True
    return False

def extract(line, extract_expr):
    """
    return tuple, the output will be 
    """
    x = re.findall("\{%(.)\}", extract_expr)
    assert len(x) == 1
    t = x[0]
    type_converter = {
        'f': float,
        'i': int,
        's': str,
    }
    type_extracter = {
        "f": '\d+\.\d+',
        "i": '\d+',
        "s": '.*',
    }
    pattern = re.sub("\{%(.)\}", "(.*?)", extract_expr, 1)
    x = re.findall(pattern, line)
    #print("DEBUG", x[0])
    if len(x) == 0: return None
    assert len(x) == 1
    return type_converter[t](x[0].strip())

def action(tuple_list, action):
    if action == "sum": 
        print (sum(tuple_list))
    if action == "mean":
        if len(tuple_list) == 0: print("null")
        else: print (sum(tuple_list) / len(tuple_list))
    if action == "print":
        for item in tuple_list: 
            print (item)

def main():
    current_step = 0
    tuple_list = []
    for line in sys.stdin:
        line = line.strip()
        if is_valid(line, args.valid_expr): 
            ret = extract(line, args.extract_expr)
            if ret: tuple_list.append(ret)
    action(tuple_list, args.reduction_expr)

if __name__ == "__main__":
    main()


