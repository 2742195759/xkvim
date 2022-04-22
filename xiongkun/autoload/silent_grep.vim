fu! SilentGrep(pattern)
    let directory_part = GetGrepDirectoryCmd()
    let save_err_format = &errorformat
    let &errorformat = &grepformat
    let output_file = tempname()
    let sh_cmd = printf("egrep -n -r \"%s\" %s > %s", a:pattern, directory_part, output_file)
    call system(sh_cmd)
    exec "cgetfile ".output_file
    " restore the options
    let &errorformat = save_err_format
endf

" 1. g:nerd_search_path is used as search start point
" 2. read the search_config file ,the file in the file is ignored

function! GetDirectorySearchConfigure()
    let search_point = g:nerd_search_path
    let search_ignore = getcwd() . "/search_config"
    let ignores = []
    if filereadable(search_ignore) == 1
        let ignores = readfile(search_ignore)
    endif
    return [search_point, ignores]
endf

function! GetGrepDirectoryCmd()
    let returns = GetDirectorySearchConfigure()
    let work_d = returns[0]
    let ignores = returns[1]
    let cmd = " " 
    for ig in ignores
        let cmd = cmd . ig . " "
    endfor
    let cmd = cmd . " " . work_d
    return cmd
endf
