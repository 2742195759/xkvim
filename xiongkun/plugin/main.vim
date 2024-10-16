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
    let search_word = expand("<cword>")
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
        let tmp = pyxeval("Xiongkun.FileSystem().exists('" . newpath . "')")
        if tmp == 0
            echom "file not exist: ".newpath
            return
        en
        execute 'py3 Xiongkun.FileSystem().edit("' . newpath . '")'
        let @/=search_word
        normal n
    en 
endf"}}}

""""""""""""""""" GitCommenter
py3 import Xiongkun

function! s:ShowGitComment()"{{{
    let filename = expand("%")
    let linenr = getcurpos()[1]
    execute 'py3' 'Xiongkun.ShowGitComment("' filename '",' str2nr(linenr) ')'
endf"}}}

function! ThreadDispatchExecutor(timer_id)"{{{
    py3 Xiongkun.PythonFunctionTimer().fire()
endfunction"}}}

function! FileTypeBranch()"{{{
    filetype detect
    if (or(&filetype == 'c',&filetype=='cpp'))
        setlocal tabstop=2 "in paddle, Default 2 for tabstop"
        setlocal shiftwidth=2 "in paddle, Default 2 for shift"
        setlocal foldmethod=marker
        setlocal foldmarker={,}
        "setlocal foldlevel=2
    elseif (&filetype == 'vim')
        setlocal commentstring=\"%s
    elseif (&filetype == 'python')
        setlocal commentstring=#%s
        setlocal foldmethod=indent
        "setlocal foldlevel=2
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
"""""""""""""""" }}}

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
vnoremap // y/\V<C-R>=escape(@",'/\')<CR><CR>
nnoremap <expr> gp '`[' . strpart(getregtype(), 0, 1) . '`]'
""" copy the visual into a tempname file. to view a part of a file
vnoremap \S  y:let tmp=&filetype<cr>:tabe <C-R>=tempname()<cr><cr>P:set filetype=tmp<cr>:set buftype=nofile<cr>:setlocal foldcolumn=0<cr>:setlocal signcolumn=no<cr>
"vnoremap K :!dict <C-R>=expand("<cword>")<cr><cr>
"

" tnoremap below.
" go back to the normal mode
noremap  <C-w>c :echo "change c-q to close"<cr>
tnoremap <C-w><C-c> :echo "change c-q to close"<cr>
tnoremap <M-e> <C-w>N  
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
tnoremap <M-o> <Cmd>JumpPrevFile<cr>
tnoremap <M-i> <Cmd>JumpNextFile<cr>

"""""""""""""""" }}}

"""""""""""""" AutoCmd {{{
let g:vim_thread_timer = 0
let g:enable_uidispatcher=1
if g:enable_uidispatcher == 1
    augroup VimThreadDispatcher
        autocmd!
        autocmd VimEnter * let g:vim_thread_timer = timer_start(10, "ThreadDispatchExecutor", {"repeat": -1})
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
    autocmd!
    autocmd InsertLeavePre  * py3 Xiongkun.windows.GlobalPreviewWindow.hide()
augroup END

augroup FileIndentAutoCommand
    autocmd!
    autocmd BufEnter * call FileTypeBranch()
augroup END

function! JustTestUIReflesh(cmd)
    " test script can update the vim ui in the background.
    " yes: redraw and redraw! is the right way to update
    let x = 10 
    while x 
        let x = x - 1
        silent execute "vne ".string(x)
        echo "hello world (y/n)" 
        redraw
        call getchar()
    endwhile
endfunction
    
""" quickjump config
function! GI()
    execute "normal `^"
    let insert_pos = getpos("'^")
    if insert_pos[2] > len(getline('.'))
        startinsert!
    else
        startinsert
    endif
endfunc

function! DispatchFilter(winid, key)
    let g:popup_handle=0
    call BufApp_PopupDispatcher([a:winid, a:key])
    return g:popup_handle
endfunction!

function! VimPopupExperiment(bufnr, filter, options, clear_buffer)
    let new_dict = a:options
    if a:filter == 1
        let new_dict['filter'] = function('DispatchFilter')
        if a:clear_buffer
            let new_dict['callback'] = function('VimPopupClose')
        endif
        let new_dict['filtermode'] = 'a'
        let new_dict['mapping'] = 0
        let new_dict['wrap'] = 0
        let new_dict['cursorline'] = get(a:options, 'cursorline', 0)
        return popup_menu(a:bufnr, new_dict)
    endif
    let new_dict['border'] = get(a:options, 'border', [])
    let new_dict['wrap'] = get(a:options, 'wrap', 0)
    let new_dict['padding'] = get(a:options, 'padding', [0, 1, 0, 1])
    let new_dict['tabpage'] = -1
    return popup_create(a:bufnr, new_dict)
endfunction

function! VimPopupClose(id, data)
    call BufApp_PopupClose([a:id, a:data])
endfunction

nnoremap <silent> s <Cmd>BufferJump<cr>
nnoremap <silent> S <Cmd>GlobalJump<cr>
nnoremap <silent> <m-w> <Cmd>WindowJump<cr>
tnoremap <silent> <m-w> <Cmd>WindowJump<cr>
vnoremap <silent> s <Cmd>BufferJump<cr>
inoremap <silent> <m-s> <Cmd>QuickPeek<cr>
"cnoremap <silent> ? <Cmd>DocPreviewUpdate<cr>

""" conflict with surrounding: cs ds ys
""" the conflict make the bugs is very hard to find. so i should install less
""" scripts as i can.
""" omap: normap + visual selection.
onoremap <silent> s v<Cmd>BufferJump<cr>

""" surround command is: 

""""""""""""""}}}
