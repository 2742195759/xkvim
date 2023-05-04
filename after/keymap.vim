" set delimate and YCM to compatible
" the keymap defined here will override
" other scripts for use of autocommand: Enterbuf 
"""""""""""""""": Key Map{{{
inoremap <buffer> <expr> <S-Tab>  pumvisible() ? "\<C-P>" : delimitMate#JumpAny()
imap <buffer> <BS>       <Plug>delimitMateBS
"nnoremap <C-P>p :call OpenCtrlpWithPath() <cr>
nnoremap <C-P><C-P> :FF<cr>
call RegisterNERDTreeKeyMap()
nnoremap    <M-1>   :tabprevious<cr>
nnoremap    <M-2>   :tabnext<cr> 
inoremap    <M-1>   <ESC>:tabprevious<cr>
inoremap    <M-2>   <ESC>:tabnext<cr> 
"""""""""""""""" }}}
