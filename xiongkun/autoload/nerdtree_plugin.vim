function! RegisterNERDTreeKeyMap()
    call NERDTreeAddKeyMap({
           \ 'key': 'gg',
           \ 'callback': 'NERDTreeAutoGrep',
           \ 'quickhelpText': 'grep in the current directory.',
           \ 'scope': 'DirNode' })

    call NERDTreeAddKeyMap({
           \ 'key': '<C-P><C-P>',
           \ 'callback': 'NERDTreeCtrlP',
           \ 'quickhelpText': 'grep in the current directory.',
           \ 'scope': 'DirNode' })

    call NERDTreeAddKeyMap({
           \ 'key': '<leader>t',
           \ 'callback': 'NERDTreeStartShell',
           \ 'quickhelpText': 'start shell in current dirnode',
           \ 'scope': 'DirNode' })

endfunction

function! NERDTreeAutoGrep(dirnode)
    echohl Directory
    let pattern = input("Grep pattern: ")
    if pattern == ""
        return
    endif
    let pattern = substitute(pattern, "|", "\\|", "g")
    echohl None
    let path = a:dirnode.path.str() 
    let cmd = 'silent! grep! -r '.pattern.' '.path.' '.'| redraw! '
    exec cmd
    let qflist = getqflist()	
    if len(qflist) > 0
        exec "normal ". "\<c-w>\<c-w>"
        if len(qflist) == 1
            exec "cc"
        else
            exec "cl"
        endif
    endif
endfunction

function! NERDTreeCtrlP(dirnode)
    let path = a:dirnode.path.str() 
    exec 'CtrlP '.path
endfunction


function! GrepUnderCursor()
    let to_search = expand('<cword>')
    let nerd_win_nr = bufwinnr('NERD')
    exe string(nerd_win_nr).'wincmd w'
    exec "normal gg ".to_search."\<cr>"
endfunction

function! NERDTreeStartShell(dirnode)
    let path = a:dirnode.path.str() 
    exec 'cd '.path
    exec 'sh'
    exec 'cd -'
endfunction


noremap <leader>f :call GrepUnderCursor()<cr>
noremap <leader>F :NERDTreeFind<cr>
