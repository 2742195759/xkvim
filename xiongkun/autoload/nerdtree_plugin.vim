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
    let cmd = 'silent! grep! -r "'.pattern.'" '.path.' '.'| redraw! | cl'
    exec cmd
endfunction

function! NERDTreeCtrlP(dirnode)
    let path = a:dirnode.path.str() 
    exec 'CtrlP '.path
endfunction
