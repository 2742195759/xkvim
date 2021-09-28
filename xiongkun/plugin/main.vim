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
        echom "filepath don't seam to be a .cc or .h, do nothing"
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
"""""""""""""""" }}}
