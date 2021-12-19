function! SaveVariable(var, file) 
    call writefile([string(a:var)], a:file) 
endfun 

function! ReadVariable(file) 
    let recover = readfile(a:file)[0] 
    " it is so far just a string, make it what it should be: 
    execute "let result = " . recover 
    return result 
endfun 

function! GetAbsolutePath(file)
endfunction

function! CreateAndImportTmpTags()
    let tmpname = "/tmp/tmp_tags"
    call system('ctags -f '.tmpname.' '.expand("%:p"))
    if match(&tags, tmpname) == -1
        exec "set tags+=".tmpname
    endif
    return tmpname
endfunction

