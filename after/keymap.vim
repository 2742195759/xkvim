" set delimate and YCM to compatible
" the keymap defined here will override
" other scripts for use of autocommand: Enterbuf 
"""""""""""""""": Key Map{{{
inoremap <buffer> <expr> <S-Tab>  pumvisible() ? "\<C-P>" : delimitMate#JumpAny()
imap <buffer> <BS>       <Plug>delimitMateBS
nnoremap <C-P>p :call OpenCtrlpWithPath() <cr>
nnoremap <C-P><C-P> :CtrlP ./<cr>
call RegisterNERDTreeKeyMap()
"""""""""""""""" }}}
