import os
import sys
import json
import time
from multiprocessing import Pool
from contextlib import contextmanager
import signal

def sssum(args):
    xs, c = args
    return [sum(xs) + c]

class KillablePool:
    """
    when kill the main process, no exception will raise in worker process.
    """
    def __init__(self, num):
        self.p = Pool(num)

    def __enter__(self):
        def handler(sig, frame):
            self.p.terminate()
            self.p.join()
            sys.exit(1)
        signal.signal(signal.SIGTERM, handler)
        return self.p

    def __exit__(self, *args):
        self.p.terminate()
        signal.signal(signal.SIGTERM, signal.SIG_DFL)

