
fu! s:DeleteUntilSlash(str)
    let new_str = substitute(a:str, "\/[^\/]*$", "\/", "")
    "let new_str = substitute(a:str, ".*", "\/", "")
    return new_str
endf

fu! CmdCtrlSlash()
    let cmd = getcmdline()
    echo cmd
    "let cmd = "/home/data/cvpack2/tests/test_rpn.py"
    let new_cmd = s:DeleteUntilSlash(cmd)
    return "\<C-U>".new_cmd
endf

cnoremap <C-A> <Home>
cnoremap <C-F> <Right>
cnoremap <C-B> <Left>
