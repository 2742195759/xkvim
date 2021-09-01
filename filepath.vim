let g:mru_files=['/home/data/cvpack2', '/home']

" used in "<C-R>=Getfiles()" to complete the command or insert
fu! Getfiles()
    let files_with_number = []
    let idx = 0
    for item in g:mru_files
        let idx += 1
        call insert(files_with_number, string(idx).'.'.item, idx-1)
    endfor
    let cmd = getcmdline()
    let inp = inputlist(files_with_number)
    return "\<C-U>".cmd.g:mru_files[inp-1]
endf
