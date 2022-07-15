""" Convenient Hight Light Word by matchadd()
let s:strkey2matchnr = {}

let s:circlegroup = ["Error", "StatusLineTerm", "Directory"]
let s:circlegroup_current = 0
fu! s:GetCircleGroup() 
    let group = s:circlegroup[s:circlegroup_current]
    let s:circlegroup_current += 1
    let s:circlegroup_current  = s:circlegroup_current % len(s:circlegroup)
    return group
endf

function! s:AddSmartMatch(pattern)
    if has_key(s:strkey2matchnr, a:pattern) 
        echom a:pattern." already highlighted"
        return 
    en
    let mid = matchadd(s:GetCircleGroup(), a:pattern)
    let s:strkey2matchnr[a:pattern] = mid
endf

function! s:DelSmartMatch(pattern)
    if has_key(s:strkey2matchnr, a:pattern) 
        call matchdelete(s:strkey2matchnr[a:pattern])
        call remove(s:strkey2matchnr, a:pattern)
        return 
    en
    echom a:pattern." not highlighted! can't delete"
endf

function! s:TriggerMatch(pattern)
    if has_key(s:strkey2matchnr, a:pattern) 
        call s:DelSmartMatch(a:pattern)
    else
        call s:AddSmartMatch(a:pattern)
    en
endf

function! s:OpenHeaderOrCpp(filepath)
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
endf

""""""""""""""""" GitCommenter
py3 import Xiongkun
function! s:ShowGitComment()
    let filename = expand("%")
    let linenr = getcurpos()[1]
    execute 'py3' 'Xiongkun.ShowGitComment("' filename '",' str2nr(linenr) ')'
endf

function! MakeXelatex()
    echo system("python3 ~/xkvim/cmd_script/xelatex.py --file=".expand("%:p"))
endfunction

function! MakeNvcc()
    let file = expand("%:p")
    call system("~/xkvim/cmd_script/remove.sh nvcc_file")
    call system("python3 ~/xkvim/cmd_script/upload.py --file " . file . " --rename nvcc_file ")
    echo system("python3 ~/xkvim/cmd_script/converse_execute.py --name xkweb --cmd " . "/home/ssd3/start_nvcc.sh")
endfunction

function! ProfileSingleScript(start_cmd)
    let file = expand("%:p")
    call system("~/xkvim/cmd_script/remove.sh profile")
    let cmd = "~/xkvim/cmd_script/send_profile_task.sh " . file . " " . '"' . a:start_cmd . '"'
    echo cmd
    echom system(cmd)
    let tmp_filename = "tmp_" . string(rand()) . ".qdrep"
    echo system(printf("python3 ~/xkvim/cmd_script/converse_execute.py --name mac --cmd " . "\"cd ~/my_report/ && curl http://10.255.125.22:8082/my_report.qdrep --output %s && open ./%s\"", tmp_filename, tmp_filename))
endfunction

function! ThreadDispatchExecutor(timer_id)
    py3 Xiongkun.vim_dispatcher.ui_thread_worker()
endfunction

function! ReloadPythonPlugin()
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
endfunction

function! FileTypeBranch()
    filetype detect
    if (or(&filetype == 'c',&filetype=='cpp'))
        "source ~/Important/MyVim/_MY_VIM_/VimCpp.vimrc
        setlocal tabstop=2 "in paddle, Default 2 for tabstop"
        setlocal shiftwidth=2 "in paddle, Default 2 for shift"
        "setlocal foldmethod=marker
        "setlocal foldmarker={,}
        setlocal foldlevel=2
    elseif (&filetype == 'vim')
        setlocal commentstring=\"%s
    elseif (&filetype == 'python')
        setlocal commentstring=#%s
        "setlocal foldmethod=indent
        setlocal foldlevel=2
        source ~/Important/MyVim/_MY_VIM_/VimPython.vimrc
    end
endfunction

packadd cfilter
packadd termdebug

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
noremap <silent> <space>m :Mt<cr>
"noremap K :!clear && dict <C-R>=expand("<cword>")<cr><cr>
"vnoremap K "dy:!clear && dict <C-R>d<cr>

noremap <C-]> <Cmd>call UniverseCtrl()<cr>
noremap <M-f> <Cmd>call UniverseSearch()<cr>
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
inoremap <M-f> <C-R>=ClangdServerComplete([])<cr>
vnoremap // y/\V<C-R>=escape(@",'/\')<CR><CR>
nnoremap <expr> gp '`[' . strpart(getregtype(), 0, 1) . '`]'
""" copy the visual into a tempname file. to view a part of a file
vnoremap \S  y:let tmp=&filetype<cr>:tabe <C-R>=tempname()<cr><cr>P:let &filetype=tmp<cr>
"vnoremap K :!dict <C-R>=expand("<cword>")<cr><cr>
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
    let index_path=getcwd().'/index.dex'
    if filereadable(index_path)
        autocmd VimEnter * execute 'ILoad '.index_path
        autocmd VimLeave * execute 'IFinish'
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

let g:enable_clangd=1
if (match(getcwd(), "/home/data/") == 0 || match(getcwd(), "/home/ssd2/") == 0)&& g:enable_clangd
    echo "Enable Clangd Server"
    "start auto cmd
    py3 Xiongkun.clangd_client._StartAutoCompile() 
endif

augroup FileIndentAutoCommand
    autocmd!
    autocmd BufEnter * call FileTypeBranch()
augroup END
""""""""""""""}}}
