""" Convenient Hight Light Word by matchadd()
let s:strkey2matchnr = {}
let s:circlegroup = ["Error", "StatusLineTerm", "Directory"]
let s:circlegroup_current = 0
fu! s:GetCircleGroup() "{{{
    let group = s:circlegroup[s:circlegroup_current]
    let s:circlegroup_current += 1
    let s:circlegroup_current  = s:circlegroup_current % len(s:circlegroup)
    return group
endf"}}}

function! s:AddSmartMatch(pattern)"{{{
    if has_key(s:strkey2matchnr, a:pattern) 
        echom a:pattern." already highlighted"
        return 
    en
    let mid = matchadd(s:GetCircleGroup(), a:pattern)
    let s:strkey2matchnr[a:pattern] = mid
endf"}}}

function! s:DelSmartMatch(pattern)"{{{
    if has_key(s:strkey2matchnr, a:pattern) 
        call matchdelete(s:strkey2matchnr[a:pattern])
        call remove(s:strkey2matchnr, a:pattern)
        return 
    en
    echom a:pattern." not highlighted! can't delete"
endf"}}}

function! s:TriggerMatch(pattern)"{{{
    if has_key(s:strkey2matchnr, a:pattern) 
        call s:DelSmartMatch(a:pattern)
    else
        call s:AddSmartMatch(a:pattern)
    en
endf"}}}

function! s:OpenHeaderOrCpp(filepath)"{{{
    " Use the execute to do actual things
    " and wrap command as call <somefunction>
    let newpath = a:filepath
    let doit = 0
    if match(a:filepath, '\.cc$') != -1
        let newpath = substitute(a:filepath, '\.cc$', '\.h', '')
        let doit = 1
    en
    if match(a:filepath, '\.h$') != -1
        let newpath = substitute(a:filepath, '\.h$', '\.cc', '')
        let doit = 1
    en
    if doit == 0
        echom "filepath don't seem to be a .cc or .h, do nothing"
    else
        execute 'e' newpath
    en 
endf"}}}

""""""""""""""""" GitCommenter
py3 import Xiongkun

function! s:ShowGitComment()"{{{
    let filename = expand("%")
    let linenr = getcurpos()[1]
    execute 'py3' 'Xiongkun.ShowGitComment("' filename '",' str2nr(linenr) ')'
endf"}}}

function! MakeXelatex()"{{{
    echo system("python3 ~/xkvim/cmd_script/xelatex.py --file=".expand("%:p"))
endfunction"}}}

function! MakeNvcc()"{{{
    let file = expand("%:p")
    call system("~/xkvim/cmd_script/remove.sh nvcc_file")
    call system("python3 ~/xkvim/cmd_script/upload.py --file " . file . " --rename nvcc_file ")
    echo system("python3 ~/xkvim/cmd_script/converse_execute.py --name xkweb --cmd " . "/home/ssd3/start_nvcc.sh")
endfunction"}}}

function! ProfileSingleScript(start_cmd)"{{{
    let file = expand("%:p")
    call system("~/xkvim/cmd_script/remove.sh profile")
    let cmd = "~/xkvim/cmd_script/send_profile_task.sh " . file . " " . '"' . a:start_cmd . '"'
    echo cmd
    echom system(cmd)
    let tmp_filename = "tmp_" . string(rand()) . ".qdrep"
    echo system(printf("python3 ~/xkvim/cmd_script/converse_execute.py --name mac --cmd " . "\"cd ~/my_report/ && curl http://10.255.125.22:8082/my_report.qdrep --output %s && open ./%s\"", tmp_filename, tmp_filename))
endfunction"}}}

function! ThreadDispatchExecutor(timer_id)"{{{
    py3 Xiongkun.vim_dispatcher.ui_thread_worker()
endfunction"}}}

function! ReloadPythonPlugin()"{{{
    py3 from importlib import reload
    py3 << endpython
import sys
from types import ModuleType
ls = [[name, mod] for name, mod in sys.modules.items()]
for name, mod in ls[::-1]:
    if name.startswith('Xiongkun'):
        m = (eval(name))
        if isinstance(m, ModuleType): reload(m)
endpython
endfunction"}}}

function! FileTypeBranch()"{{{
    filetype detect
    if (or(&filetype == 'c',&filetype=='cpp'))
        setlocal tabstop=2 "in paddle, Default 2 for tabstop"
        setlocal shiftwidth=2 "in paddle, Default 2 for shift"
        setlocal foldmethod=marker
        setlocal foldmarker={,}
        setlocal foldlevel=2
    elseif (&filetype == 'vim')
        setlocal commentstring=\"%s
    elseif (&filetype == 'python')
        setlocal commentstring=#%s
        setlocal foldmethod=indent
        setlocal foldlevel=2
    end
endfunction"}}}

packadd cfilter"{{{
packadd termdebug"}}}

"""""""""""""""": HighLight Group {{{
hi ListBoxKeyword term=bold ctermfg=208 ctermbg=24
hi ListBoxLine term=bold ctermbg=24
""""""""""""""}}}

"""""""""""""""": Command below {{{
com! -n=0 Mt cal s:TriggerMatch(expand('<cword>'))
com! -n=0 CC cal s:OpenHeaderOrCpp(expand('%'))
com! -n=0 Latex cal MakeXelatex()
com! -n=0 Nvcc cal MakeNvcc()
com! -n=1 Profile cal ProfileSingleScript(<args>)
com! -n=0 Reload cal ReloadPythonPlugin()
"""""""""""""""" }}}

function! IMAP_EXECUTE_PY3(py3_stmt)"{{{
    execute "py3 " . a:py3_stmt
    return "\<Ignore>"
endfunction"}}}

"""""""""""""""": Map below {{{
nnoremap <silent> <space>m :Mt<cr>
"noremap K :!clear && dict <C-R>=expand("<cword>")<cr><cr>
"vnoremap K "dy:!clear && dict <C-R>d<cr>

nnoremap <C-]> <Cmd>call UniverseCtrl()<cr>
nnoremap <M-s> <Cmd>call UniverseSearch()<cr>
nnoremap <M-p> <Cmd>py3 Xiongkun.windows.GlobalPreviewWindow.find()<cr>
nnoremap <M-j> <Cmd>py3 Xiongkun.windows.GlobalPreviewWindow.next()<cr>
nnoremap <M-k> <Cmd>py3 Xiongkun.windows.GlobalPreviewWindow.prev()<cr>
nnoremap <M-h> <Cmd>py3 Xiongkun.windows.GlobalPreviewWindow.page_up()<cr>
nnoremap <M-l> <Cmd>py3 Xiongkun.windows.GlobalPreviewWindow.page_down()<cr>
nnoremap <M-u> <Cmd>py3 Xiongkun.windows.GlobalPreviewWindow.open_in_preview_window()<cr>
inoremap <M-p> <C-o>:call SearchFunctionWhileInsert()<cr>
inoremap <M-j> <Cmd>py3 Xiongkun.windows.GlobalPreviewWindow.next()<cr>
inoremap <M-k> <Cmd>py3 Xiongkun.windows.GlobalPreviewWindow.prev()<cr>
inoremap <M-h> <Cmd>py3 Xiongkun.windows.GlobalPreviewWindow.page_up()<cr>
inoremap <M-l> <Cmd>py3 Xiongkun.windows.GlobalPreviewWindow.page_down()<cr>
inoremap <M-u> <Cmd>py3 Xiongkun.windows.GlobalPreviewWindow.open_in_preview_window()<cr>
inoremap <M-g> <C-R>=ClangdServerComplete([])<cr>
vnoremap // y/\V<C-R>=escape(@",'/\')<CR><CR>
nnoremap <expr> gp '`[' . strpart(getregtype(), 0, 1) . '`]'
""" copy the visual into a tempname file. to view a part of a file
vnoremap \S  y:let tmp=&filetype<cr>:tabe <C-R>=tempname()<cr><cr>P:set filetype=tmp<cr>:set buftype=nofile<cr>
"vnoremap K :!dict <C-R>=expand("<cword>")<cr><cr>
"

" tnoremap below.
" go back to the normal mode
noremap  <C-w>c :echo "change c-q to close"<cr>
tnoremap <C-w><C-c> :echo "change c-q to close"<cr>
tnoremap <M-n> <C-w>N  
" copy and paste by the vim register
tnoremap <M-p> <C-w>""  
" forcefully exit the ternimal mode
tnoremap <M-q> <C-w><C-c>
" switch between tab pages.
tnoremap <M-1> <C-w>gT
tnoremap <M-2> <C-w>gt
" insert command
tnoremap <F1> <C-w>:BashHelp<cr>
" abbre in terminal mode
tnoremap <M-a>xk  xiongkun
tnoremap <M-a>pdb import pdb; pdb.set_trace()
tnoremap <M-a>pro export http_proxy=http://172.19.57.45:3128<cr>export https_proxy=http://172.19.57.45:3128<cr>
tnoremap <M-a>nop unset http_proxy<cr>unset https_proxy
tnoremap <M-a>pp PYTHONPATH="/home/data/Paddle2/Paddle/build/python"
tnoremap <M-a>vd CUDA_VISIBLE_DEVICES=3
tnoremap <M-a>up /home/data/web/scripts/copy_file.sh
tnoremap <M-a>def paddle.static.default_main_program()

"""""""""""""""" }}}

"""""""""""""" AutoCmd {{{
let g:vim_thread_timer = 0
let g:enable_uidispatcher=1
if g:enable_uidispatcher == 1
    augroup VimThreadDispatcher
        autocmd!
        autocmd VimEnter * let g:vim_thread_timer = timer_start(200, "ThreadDispatchExecutor", {"repeat": -1})
        autocmd VimLeave * let g:vim_thread_timer = timer_stop(g:vim_thread_timer)
    augroup END
endif

augroup UniverseCtrlGroup
    autocmd!
    autocmd VimEnter * cal g:universe_searcher.Init()
    let index_path=getcwd().'/index.idx'
    if filereadable(index_path)
        "autocmd VimEnter * execute 'ILoad '.index_path
        "autocmd VimLeave * execute 'IFinish'
    endif
    autocmd VimLeave * cal g:universe_searcher.Exit()
augroup END

function! TryOpenPreview()
    if g:enable_insert_preview == 1
        call SearchFunctionWhileInsert()
    endif
endfunc

augroup PopupPreview
    "autocmd!
    "autocmd CursorMovedI * cal TryOpenPreview()
    autocmd InsertLeave  * py3 Xiongkun.windows.GlobalPreviewWindow.hide()
    "autocmd CursorHoldI * cal TryOpenPreview()
augroup END

augroup FileIndentAutoCommand
    autocmd!
    autocmd BufEnter * call FileTypeBranch()
augroup END


""" quickjump config

function! VimQuickJump(cmd)
    if a:cmd == 's'
        exe 'BufferJump '. a:cmd
    elseif a:cmd == 'S'
        exe 'GlobalJump '. a:cmd
    elseif a:cmd == 't'
        exe 'WindowJump '. a:cmd
    endif
    let loop_num = 20
    while loop_num > 0
        let t = pyxeval("Xiongkun.jump_state.is_stop")
        if t == 1
            break
        endif
        redraw
        QuickJump
        let loop_num = loop_num - 1
    endwhile
endfunc

function! GI()
    execute "normal `^"
    let insert_pos = getpos("'^")
    if insert_pos[2] > len(getline('.'))
        startinsert!
    else
        startinsert
    endif
endfunc

function! VimInsertQuickPeek()
    call VimQuickJump('s')
    """ normal can't go into insert mode
    execute "normal \<m-p>"
    call GI()
endfunction

function! RPCServer(channel, msg)
    let g:rpc_receive=a:msg
    "echom a:msg
    py3 Xiongkun.rpc_server.receive()
endfunction

function! RPCServerError(channel, msg)
    let g:rpc_receive=a:msg
    echom a:msg
endfunction
    

nnoremap <silent> s <Cmd>call VimQuickJump('s')<cr>
nnoremap <silent> S <Cmd>call VimQuickJump('S')<cr>
nnoremap <silent> <tab> <Cmd>call VimQuickJump('t')<cr>
vnoremap <silent> s <Cmd>call VimQuickJump('s')<cr>
inoremap <silent> <m-s> <esc>:<c-u>call VimInsertQuickPeek()<esc>


""" conflict with surrounding: cs ds ys
""" the conflict make the bugs is very hard to find. so i should install less
""" scripts as i can.
""" omap: normap + visual selection.
onoremap <silent> s v<Cmd>call VimQuickJump('s')<cr>

""" surround command is: 

""""""""""""""}}}

