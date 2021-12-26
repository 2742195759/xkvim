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

"""""""""""""""": Command below {{{
com! -n=0 Mt cal s:TriggerMatch(expand('<cword>'))
com! -n=0 CC cal s:OpenHeaderOrCpp(expand('%'))
com! -n=0 GG cal s:ShowGitComment()
"""""""""""""""" }}}

"""""""""""""""": Map below {{{
noremap <silent> <space>m :Mt<cr>
noremap K :!clear && dict <C-R>=expand("<cword>")<cr><cr>
vnoremap K "dy:!clear && dict <C-R>d<cr>:set filtype=

noremap <C-]> :call UniverseCtrl()<cr>
noremap <M-f> :call UniverseSearch()<cr>
nnoremap <M-p> :call TagPreviewTrigger()<cr>
inoremap <M-p> <C-o>:call SearchFunctionWhileInsert()<cr>
""" copy the visual into a tempname file. to view a part of a file
vnoremap \S  y:let tmp=&filetype<cr>:tabe <C-R>=tempname()<cr><cr>P:let &filetype=tmp<cr>
"vnoremap K :!dict <C-R>=expand("<cword>")<cr><cr>
"""""""""""""""" }}}

"""""""""""""" AutoCmd {{{

augroup UniverseCtrl
    autocmd!
    autocmd VimEnter * cal g:universe_searcher.Init()
    autocmd VimLeave * cal g:universe_searcher.Exit()
augroup END

function! TryOpenPreview()
    if g:enable_insert_preview == 1
        call SearchFunctionWhileInsert()
    endif
endfunc

augroup PopupPreview
    autocmd!
    autocmd CursorMovedI * cal TryOpenPreview()
    autocmd InsertLeave  * cal g:previewer.reset()
    "autocmd CursorHoldI * cal TryOpenPreview()
augroup END
""""""""""""""}}}
