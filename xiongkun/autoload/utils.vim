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
