from threading import Thread, Lock, currentThread
from queue import Queue
import traceback
import time
from contextlib import contextmanager
import ctypes
import inspect
from .log import log
import multiprocessing

def _async_raise(tid, exctype):# {{{
    """ throw a exception in a thread.
    """
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")# }}}

def stop_thread(thread):# {{{
    _async_raise(thread.ident, SystemExit)
    thread.join()# }}}

class CancellableWorker:# {{{
    def __init__(self, worker_func):
        self.fn = worker_func
        pass

    def __call__(self, *args, **kargs):
        return self.fn(*args, **kargs)

    def cancel(self):
        pass# }}}
        
@contextmanager
def ExceptionCatch():# {{{
    # TODO (add no change quick fix guard)
    try : 
        yield
    except Exception as e: 
        exstr = traceback.format_exc()
        log ("[ConsumerCallback Error]:", exstr) # }}}

class Model:# {{{
    def destory(self):
        pass

    def start(self):
        pass# }}}

class ProductConsumerModel(Model):#{{{
    def __init__(self, producers, consumer_callback, done_callback=None):
        self.queue = Queue()
        self.producers = producers
        self.callback = consumer_callback
        self.done_callback = done_callback
        self.threads = []
        self.done = 0 # consumer wrapper

    def is_done(self):
        return self.done == len(self.producers)

    def consumer_wrapper(self, queue, args):
        while self.done < len(self.producers):
            try:
                objs = queue.get(timeout=1)
            except Exception as e: 
                continue
            try:
                if objs is None: assert False
                self.done += 1
                self.callback(objs, *args)
            except Exception as e: 
                log ("[ConsumerCallback Error]:", e)
                exstr = traceback.format_exc()
                log(exstr)
                break

        if self.is_done() and self.done_callback: 
            try:
                self.done_callback(*args)
            except Exception as e: 
                log ("[DoneCallback Error]:", e)
                exstr = traceback.format_exc()

    def producer_wrapper(self, queue, fn, args):
        try:
            results = fn(*args)
            queue.put(results)
        except SystemExit as e: 
            queue.put([])
            pass
        except Exception as e: 
            log("[ProducerError]:", e)
            exstr = traceback.format_exc()
            log(exstr)
            queue.put([])

    def destory(self):
        #if self.producers_cancels is not None:
            #for c in self.producers_cancels:
                #c()
        #for t in self.threads:
            #t.join()
        self.threads = []

    def start(self, args=[]):
        try: 
            self.threads.append(Thread(target=self.consumer_wrapper, args=(self.queue, args), daemon=True))
            for p in self.producers:
                self.threads.append(Thread(target=self.producer_wrapper, args=(self.queue, p, args), daemon=True))
            for t in self.threads:
                t.start()
        except:
            exstr = traceback.format_exc()
            log(exstr)# }}}

class UIDispatcher(Model):# {{{
    """ example:
        
        dispatcher = UIDispatcher()

        [execute thread:]
            while True: # or timer
                dispatch.ui_thread_worker()

        [other thread:]
            def fn(a, b, c):
                log(a,b,c)  # this function will be executed in execute thread.
                
            dispatch.call(fn, [a, b, c])
    """
    class CallRequest:
        def __init__(self, fn, args=[]):
            self.fn = fn
            self.args = args

        def execute(self):
            return self.fn(*self.args)

    def __init__(self):
        self.queue = Queue()
        self.reply = Queue()
        self.main_id = currentThread().ident

    def is_main(self):
        return self.main_id == currentThread().ident

    def ui_thread_worker(self, block=False, timeout=0.5):
        """ main ui thread call this function to check queue and execute it.
        """
        try:
            call_req = self.queue.get(block=False)
            ret = None
            try:
                ret = call_req.execute()
            except Exception as e:
                log('[UI-Thread Error]:', e)
                exstr = traceback.format_exc()
                log(exstr)
            self.reply.put(ret)
        except:
            pass

    def call(self, fn, args=[]):
        """ non-ui thread can call this function.
            the fn will be dispatched to main thread.
        """
        if self.is_main(): # in main thread: call directly
            return fn(*args)
        self.queue.put(UIDispatcher.CallRequest(fn, args))
        return self.reply.get()# }}}

class ThreadRemoteService:
    """
    in vim + python, thread busy will cause ui thread busy
    useless !!
    """
    def __init__(self, worker):
        self.id = 0
        self.worker = worker
        self.queue = multiprocessing.Queue()
        self.threads = []

    def __call__(self, args, on_finish): 
        self.id += 1
        cur_id = self.id
        def worker(*args):
            output = self.worker(*args)
            return (cur_id, output)

        def finish(id, output):
            if cur_id == self.id: 
                if isinstance(output, tuple): 
                    on_finish(*output)
                else: 
                    on_finish(output)

        thread_run(worker, args=args, on_finish=finish)

def thread_run(func, args=[], on_finish=None, on_error=None):
    def wrapper_func(*args, **kwargs):
        try:
            output = func(*args, **kwargs)
            if isinstance(output, tuple): 
                on_finish(*output)
            else: 
                on_finish(output)
        except Exception as e:
            log("Thread Run Exception: ", str(e))
            if on_error is not None: 
                on_error(e)

    thread = Thread(target=wrapper_func, args=args, daemon=True)
    thread.start()

def test():# {{{
    def p1(inp):
        time.sleep(3)
        return 3 + inp

    def p2(inp):
        time.sleep(5)
        xxx
        return 5 + inp

    def echo(objs, inp):
        log(objs)

    pcm = ProductConsumerModel([p1, p2], echo)
    pcm.start(args=[2])# }}}
