fu! SilentGrep(pattern, path)
    let save_err_format = &errorformat
    let &errorformat = &grepformat
    let output_file = tempname()
    let sh_cmd = printf("egrep -n -r \"%s\" %s > %s", a:pattern, a:path, output_file)
    call system(sh_cmd)
    exec "cgetfile ".output_file
    " restore the options
    let &errorformat = save_err_format
endf
