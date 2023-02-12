let g:nerd_search_path = getcwd()

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

    call NERDTreeAddKeyMap({
           \ 'key': 'S',
           \ 'callback': 'NERDTreeChangeSearchPath',
           \ 'quickhelpText': 'change current search path',
           \ 'scope': 'DirNode' })

endfunction

function! NERDTreeAutoGrep(dirnode)
    echohl Directory
    let pattern = input("Grep pattern: ")
    if pattern == ""
        return
    endif
    let pattern = shellescape(pattern)
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

function! NERDTreeChangeSearchPath(dirnode)
    let path = a:dirnode.path.str() 
    let g:nerd_search_path = path
    echoh Question
    echom "change search path: ".path
    echoh None
endf


nnoremap <leader>f :call GrepUnderCursor()<cr>
nnoremap <leader>F :NERDTreeFind<cr>
