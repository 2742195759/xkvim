
fu! s:DeleteUntilSlash(str)
    let new_str = substitute(a:str, "\/[^\/]*$", "\/", "g")
    "let new_str = substitute(a:str, ".*", "\/", "g")
    return new_str
endf

fu! CmdCtrlSlash()
    let cmd = getcmdline()
    if cmd[-1:-1] == '/'
        let cmd = cmd[0:-2]
    endif
    let new_cmd = s:DeleteUntilSlash(cmd)
    return "\<C-U>".new_cmd
endf

cnoremap <C-A> <Home>
cnoremap <C-F> <Right>
cnoremap <C-B> <Left>
"cnoremap <C-/> <Cmd>call CmdCtrlSlash()<CR>
cnoremap <expr> <C-s> CmdCtrlSlash()
