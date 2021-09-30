let g:mru_files=['./', '/home/data/cvpack2/', '/home/data/Paddle/']
"{{{
" used in "<C-R>=Getfiles()" to complete the command or insert
fu! s:StartFileInputList()
    let files_with_number = []
    let idx = 0
    for item in g:mru_files
        let idx += 1
        call insert(files_with_number, string(idx).'.  '.item, idx-1)
    endfor
    let inp = inputlist(files_with_number)
    return g:mru_files[inp-1]
endf
"}}}
fu! Getfiles()
    let cmd = getcmdline()
    let filepath = s:StartFileInputList()
    return "\<C-U>".cmd.filepath
endf

fu! OpenCtrlpWithPath()
    let filepath = s:StartFileInputList()
    echom "CtrlP".filepath
    execute 'CtrlP' filepath
endf
