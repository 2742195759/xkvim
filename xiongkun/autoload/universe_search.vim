function! KeyworkSearch()
    let context = [
    \ ["show &function list", "call quickui#tools#list_function()"], 
    \ ["&translation", "execute('!clear && dict <C-R>=expand(\"<cword>\")<cr><cr>"], 
    \ ["Jump File name", ""], 
    \ ["Jump Tag name", ""], 
    \ ["Jump YCM &definition", "YcmCompleter GoToDefinition"], 
    \ ]
    call quickui#context#open(context, {})
endfunction

nmap U :call KeyworkSearch()<cr>
