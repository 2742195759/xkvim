" set delimate and YCM to compatible
inoremap <buffer> <expr> <S-Tab>  pumvisible() ? "\<C-P>" : delimitMate#JumpAny()
imap <buffer> <BS>       <Plug>delimitMateBS

