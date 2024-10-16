from .vim_utils import *
import vim
from .func_register import *

class RegionPainter:
    def __init__(self, unique_name):
        self.name = unique_name
        self.group_name = "XK" + self.name
        hi_cmd = f"hi {self.group_name} ctermbg=238"
        vim.command(hi_cmd)
        self.match_id = None

    def color(self, region, bgcolor=238):
        """
        start_line = region[0]
        end_line = region[1]
        start_col = region[2]
        end_col = region[3]
        """
        self.clear()
        hi_cmd = f"hi {self.group_name} ctermbg={bgcolor}"
        vim.command(hi_cmd)
        region = fr"\%>{region[0]}l\&\%<{region[1]}l\&\%>{region[2]}c\&\%<{region[3]}c"
        print(f"matchadd('{self.group_name}', '{region}')")
        self.match_id = vim.eval(f"matchadd('{self.group_name}', '{region}', -1)")
        
    def clear(self):
        if self.match_id is not None: 
            vim.eval(f"matchdelete({self.match_id})")

painter = RegionPainter("fold")

@vim_register(keymap="<space>z")
def MarkCurrentFold(args):
    with CursorGuard():
        vim.command('normal [z')
        startline = GetCursorXY()[0]
        vim.command('normal ]z')
        endline = GetCursorXY()[0]

    painter.color([startline-1, endline+1, 0, 1000])

    #syn_cmd = f"syn region XKFoldHighLight start=/\%{startline}l/ end=/\%{endline+1}l/"
    #vim.command("syntax clear XKFoldHighLight")
    #vim.command(hi_cmd)
    #vim.command(syn_cmd)
