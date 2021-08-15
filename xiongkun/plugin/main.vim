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

"""""""""""""""": Command below {{{

com! -n=0 Mt cal s:TriggerMatch(expand('<cword>'))
"""""""""""""""" }}}


"""""""""""""""": Map below {{{
noremap <buffer> <silent> <space>m :Mt<cr>
"""""""""""""""" }}}
