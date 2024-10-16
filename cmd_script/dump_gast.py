import gast
def parameter_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Support Args:")
    parser.add_argument("--code",                 type=str,   default="x = 10",  help="code block to dump")
    parser.add_argument("--file",                 type=str,   default=None,  help="the file contain multi-line code.")
    return parser.parse_args()

args = parameter_parser()
code = args.code
file = args.file
if file is not None: 
    with open(file, "r") as fp :
        codes = fp.readlines()
        assert len(codes) >= 1, "At least one line code in file."
        import re
        codes[0] = re.sub("^\s*", "", codes[0])
    code = "".join(codes)
module = gast.parse(code)
#import pprintast
print(gast.dump(module.body[0]))

