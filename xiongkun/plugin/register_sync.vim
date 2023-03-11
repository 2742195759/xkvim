let g:last_ftime = -1
let g:sync_timer = -1
function! s:RegisterSyncRead(timer_id)
    " read the yank file, and set the register
    let filepath = expand('~/.vim_yank.txt')
    let last_ftime = getftime(filepath)
    if last_ftime > g:last_ftime
        let lines = readfile(filepath, 'r')
        if len(lines)> 0
            let regname = lines[0]
            call setreg(regname, lines[2:], lines[1])
            let last_ftime = last_ftime
        endif
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
    let filepath = expand('~/.vim_yank.txt')
    "if v:event['regname'] == '"'
    "let reg_to_sync = getreginfo()['points_to']
    let lines =  copy(v:event['regcontents'])
    let lines = insert(lines, v:event['regtype'], 0)
    let lines = insert(lines, '"')
    cal writefile(lines, filepath, 's')
    let g:last_ftime = getftime(filepath) "prevent the self read.
    "endif
endfunction

augroup RegisterSync
    autocmd!
    autocmd TextYankPost * cal s:RegisterSyncWrite()
augroup END

call s:StartSyncTimer()
