let g:last_ftime = -1
let g:sync_timer = -1
function! s:RegisterSyncRead(timer_id)
    " read the yank file, and set the register
    let filepath = expand('~/.vim_yank')
    let last_ftime = getftime(filepath)
    if last_ftime > g:last_ftime
        let regname = '"'
        let lines = readfile(filepath, 'r')
        call setreg(regname, lines)
        let last_ftime = last_ftime
    endif
endf

function! s:StartSyncTimer()
    if g:sync_timer != -1
        call timer_stop(g:sync_timer)
    endif 
    let g:sync_timer =  timer_start(1000, function("s:RegisterSyncRead"), {'repeat': -1})
endfunction

function! s:RegisterSyncWrite() 
    " different container should have this softlink to 
    " sync the register of yank.
    let filepath = expand('~/.vim_yank')
    if v:event['operator'] == 'y'
        let lines =  v:event['regcontents']
        cal writefile(lines, filepath, 's')
    endif
endfunction

augroup RegisterSync
    autocmd!
    autocmd TextYankPost * cal s:RegisterSyncWrite()
augroup END

call s:StartSyncTimer()
