import os
import sys
import json
import time
import multiprocessing as mp
from log import log

queue = mp.Queue()
def QueueLoop(process_fn):
    log("[Server]: Start queue loop.")
    while True:
        output = queue.get()
        log(f"[Server]: Queue Get! {output}")
        process_fn(output)
