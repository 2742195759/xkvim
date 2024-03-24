import visdom
import sys
import numpy as np
def parameter_parser():
    import argparse
    parser = argparse.ArgumentParser(description="Support Args:")

    parser.add_argument("--host",                 type=str,   default="http://10.255.125.22/",  help="data path")
    parser.add_argument("--port",                 type=str,   default="8088",  help="data path")
    parser.add_argument("--name",                 type=str,   default="validation",  help="data path")
    parser.add_argument("--title",                type=str,   default="loss",  help="title of the graph")

    return parser.parse_args()

args = parameter_parser()
viz = visdom.Visdom(args.host, port=args.port, env="model_" + args.name)

losses = []
for loss in sys.stdin: 
    val = float(loss.strip())
    losses.append(val)

viz.line(X=np.arange(0, len(losses)), Y=losses, name="loss line", opts={"title":args.title})
