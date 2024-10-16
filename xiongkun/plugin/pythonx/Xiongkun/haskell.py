from . import vim_utils
import vim
from .func_register import *
from .rpc import rpc_call
from .command_doc_popup import DocPreviewBuffer
from .windows import GPW, PreviewWindow

@vim_register(keymap="<c-[>", command="Hoogle", with_args=True)
def HoogleSearch(args):
    if len(args) == 0: keyword = vim_utils.GetCurrentWord()
    else: keyword = args[0]
    def on_return(markdown_docs):
        docs = [ PreviewWindow.ContentItem("keyword", doc.split("\n"), "markdown", 1) for doc in markdown_docs ]
        GPW.set_showable(docs)
        if GPW.hidden: GPW.show()
    if not GPW.hidden: 
        GPW.trigger()
    else:
        rpc_call("hoogle.search", on_return, keyword)
