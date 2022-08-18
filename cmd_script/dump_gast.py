import gast
def parameter_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Support Args:")
    parser.add_argument("--code",                 type=str,   default="x = 10",  help="code block to dump")
    return parser.parse_args()
args = parameter_parser()
code = args.code
module = gast.parse(code)
print (gast.dump(module.body[0]))

