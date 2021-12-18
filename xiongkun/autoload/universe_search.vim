"----------------------------------------------------------------------
" internal variables
"----------------------------------------------------------------------
"
let s:searcher = {
\'cwd': ""
\}
let s:previewer = {
\ 'winid': -1, 
\ 'bufid': -1,
\}

" Global Setting 
" g:jump_cmd   set the jump cmd, tabe | e | vertical e
"
let g:jump_cmd="e"
let g:max_filename_length=35
let g:max_text_length=90
let g:enable_ycm=1

function! s:previewer.reset()
    if self.bufid != -1
        "silent! exec printf('bdelete %d', self.bufid)
        let self.bufid = -1
    endif
    if self.winid != -1
        silent! call popup_close(self.winid)
        let self.winid = -1
    endif
endfunction

""{{{
function! s:previewer.preview(filename, linenr, opts)
  call self.reset()
  let bufnr = bufadd(a:filename)
  call bufload(bufnr)
  let self.bufid = bufnr
  let maxheight = get(a:opts, 'maxheight', 9)
  let options = {
        \ 'pos':    'topleft',
        \ 'border': [],
        \ 'title':  a:filename
        \ }
  call extend(options, g:quickpeek_popup_options)
  call extend(options, {
        \ 'maxheight': maxheight,
        \ 'minwidth':  a:opts.width,
        \ 'minheight': 5,
        \ 'maxwidth':  a:opts.width,
        \ 'col':       a:opts.col,
        \ 'line':      a:opts.line,
        \ 'posinvert': 0, 
        \ })
  silent let self.winid  = popup_create(bufnr, options)
  for setting in g:quickpeek_window_settings
    call win_execute(self.winid, 'silent setlocal '.setting)
  endfor
  call win_execute(self.winid, 'silent normal! '.a:linenr.'Gzz')
endfunction
""}}}

let s:searcher.history = []
let s:searcher.status = {}
let s:searcher.is_preview = 0

let g:universe_searcher = s:searcher

"{{{
function! s:searcher.preview_toggle()
    if self.is_preview == 0
        let self.is_preview = 1
    else 
        let self.is_preivew = 0
        call s:previewer.reset()
    endif
endfunction
"}}}
"----------------------------------------------------------------------
" init
"   item have keys : 
"       filename : the filename 
"       lnum     : the line number
"       text     : the text of results. one line
"       cmd      : cmd to jump to the file and lines
"       source   : where is the data from. which searcher.
"       other    : where is the data from. which searcher.
"----------------------------------------------------------------------
function! KeyworkSearch()
    let context = [
    \ ["show &function list", "call quickui#tools#list_function()"], 
    \ ["&translation", "execute('!clear && dict <C-R>=expand(\"<cword>\")<cr><cr>"], 
    \ ["Jump File name", ""], 
    \ ["Jump Tag name", ""], 
    \ ["Jump YCM &definition", "YcmCompleter GoTo"], 
    \ ]
    call quickui#context#open(context, {})
endfunction

nmap U :call KeyworkSearch()<cr>

function! s:searcher.search_and_render(input_text, cwd)
    let self.cwd = a:cwd
    if self.cwd == ""
        let self.cwd = expand("%:p:h")
    endif
    let ret = self.search(a:input_text)
    let self.cwd = ""
    call self.render(ret, a:input_text)
endf

function! s:searcher.search(input_text)
    let results = []
    if g:enable_ycm == 1
        let results = results + YCMSearcher(self, a:input_text)
    endif
    let results = results + CtagSearcher(self, a:input_text)
    let results = results + GrepSearcher(self, a:input_text)
    return results
endfunction

function! s:StringTrimer(str, max_len)
    if a:max_len < len(a:str)
        return '|...' . a:str[-a:max_len:] . '|'
    else
        return '|' . a:str . '|'
    endif
endfunction

function! s:FilenameTrimer(filename)
    return s:StringTrimer(a:filename, g:max_filename_length)
endfunction

function! s:TextTrimer(text)
    if g:max_text_length < len(a:text)
        return a:text[0:g:max_text_length-1] . "..."
    else
        return a:text
    endif
endfunction

function! s:searcher.unique(results)
    let unique_set = {} 
    let ret = []
    for item in a:results
        let linenr = s:PeekLineNumber(item)
        let item['lnum'] = linenr
        let filename = fnamemodify(item["filename"], ":p")
        let key = filename . linenr
        if get(unique_set, key, 0) == 0
            let unique_set[key] = 1
            call add(ret, item)
        endif
    endfor
    return ret
endf

function! s:SetqfList(results)
    call setqflist(a:results)
endfunc

function! s:IsIgnored(ignore_list, idx, item)
    let absfilename = fnamemodify(a:item["filename"], ":p")
    for ig in a:ignore_list
        let m = matchstr(absfilename, ig)
        if m == absfilename
            " matched, ignore this one, return 0 to discard
            return 0
        endif
    endfor
    return 1
endf

function! s:GetIgnoreList()
    let filename = getcwd()."/ignore"
    let bufnr = bufadd(filename)
    call bufload(bufnr)
    let lines = getbufline(bufnr, 1, "$") 
    return lines
endfunc

function! s:searcher.apply_filter(results)
    let ignore_list = s:GetIgnoreList()
    call filter(a:results, function('s:IsIgnored', [ignore_list]))
    return a:results
endf
    

function! s:searcher.render(results, title)
    " [unique]
    "
    let results = self.unique(a:results)
    " [filter]
    "
    let l:results = self.apply_filter(l:results)
    call s:SetqfList(l:results)
    " [render]
    "
    " render to boxlist
        " 1. first get the text and cmd.
        " 2. text is aligned by '\t'
    let to_render = []
    let idx = 1
    for item in l:results
        let render_item = ["", ""]
        let render_item[0] = join([idx, item["source"], trim(get(item, 'other', '')), s:FilenameTrimer(item["filename"]), s:TextTrimer(trim(item["text"]))], "\t")
        let render_item[1] = printf("call ExecuteJumpCmd('%s', '%s')", item.filename, item.cmd)
        call add(to_render, render_item)
        let idx += 1
    endfor 
    let self.hwnd = quickui#listbox#open(to_render, {'h': 20, 'title': a:title, 'syntax': 'search'})
    silent call win_execute(self.hwnd.winid, printf("match Search /%s/", a:title))
    let oldopt = popup_getoptions(self.hwnd.winid)
	let self.hwnd.old_filter = oldopt["filter"]
    let self.hwnd.old_callback = oldopt["callback"]
    let self.hwnd.raw = l:results
    let oldopt.filter = function('s:CustomedKeyMap')
    let oldopt.callback = function('s:CustomedCallback')
    call popup_setoptions(self.hwnd.winid, oldopt)
endfunction

function! s:CustomedCallback(winid, code)
	let local = quickui#core#popup_local(a:winid)
	let hwnd = local.hwnd
    let OldFunc = hwnd.old_callback
    let s:searcher.is_preview = 0
    call s:previewer.reset()
    call hwnd.old_callback(a:winid, a:code)
endfunction

function! s:GetPreviewRectangle(winid)
    let info = popup_getpos(a:winid)
    let ret = {}
    let ret.col = info.col
    let ret.line = info.line + info.height
    let ret.width = info.width
    let ret.height = 9
    return ret
endfunction

function! s:CustomedKeyMap(winid, key)
	let local = quickui#core#popup_local(a:winid)
	let hwnd = local.hwnd
    let OldFunc = hwnd.old_filter
    if a:key == 'p'
        call s:searcher.preview_toggle()
    endif
    
    let ret = OldFunc(a:winid, a:key)
    " after call old filter
    if s:searcher.is_preview == 1
        call win_execute(a:winid, "silent let @q=line('.')")
        let cur_selected = str2nr(@q) - 1
        let filename = hwnd.raw[cur_selected].filename
        let linenr = s:PeekLineNumber(hwnd.raw[cur_selected])
        call s:previewer.preview(filename, linenr, s:GetPreviewRectangle(a:winid))
        let cmd = hwnd.raw[cur_selected].cmd
    endif
    return ret
endfunction






function! CtagSearcher(searcher, input_text)
    let items = taglist(a:input_text)
    for item in items
        let item["source"] = "CTag"
        let item["other"]  = item.kind
        let item["text"]  =  trim(item.cmd, "\\/^$ \t")
    endfor
    return items
endfunction

function! CtrlPSearcher(searcher, input_text)
endfunction

function! YCMSearcher(searcher, input_text)
    let item = TryYcmJumpAndReturnLocation(a:input_text)
    if item[1] == -1
        return []
    endif
    return [{"filename": item[0], "lnum": item[1], "cmd": printf(":%d", item[1]), "other":"", "source":"YCM", "text":item[2]}]

endfunction

function! GrepSearcher(searcher, input_text)
    let pattern = shellescape(a:input_text)
    let path = a:searcher.cwd
    let cmd = 'silent! grep! -r '.pattern.' '.path.' '.'| redraw! '
    silent exec cmd
    let qflist = getqflist()	
    let ret = []
    if len(qflist) > 0
        for qfitem in qflist
            if qfitem.valid
                let item = {'source': 'Grep', "other":""}
                let item.filename = bufname(qfitem.bufnr)
                let item.lnum = qfitem.lnum
                let item.text = tr(qfitem.text, "\t", " ")
                let item.cmd  = printf(":%d", item.lnum)
                call add(ret, item)
            endif
        endfor
    endif
    return ret
endfunction

function! ExecuteJumpCmd(filename, cmd)
    let cmd = escape(a:cmd, "~*.")
    silent exec printf("%s %s",g:jump_cmd, fnameescape(a:filename))
    silent exec l:cmd
endfunction

function! s:PeekLineNumber(universe_item)
    if get(a:universe_item, 'lnum', -1) != -1
        return a:universe_item['lnum']
    elseif a:universe_item['cmd'][0] == "/"
        return s:PeekLineNumberFromSearch(a:universe_item['filename'], a:universe_item['cmd'])
    else
        return 0
endfunction

function! s:PeekLineNumberFromSearch(filename, search_cmd)
    let search_cmd = escape(a:search_cmd, "~*.")
    let new_buf = bufadd(a:filename)
    call bufload(new_buf)
    let lines = getbufline(new_buf, 1, '$')
    let line_nr = match(lines, trim(search_cmd, "/")) + 1
    return line_nr
endfunction

" slow but bug free
function! s:PeekLineNumberFromCMD(filename, search_cmd) abort
    let new_buf = bufadd(a:filename)
    call bufload(new_buf)
    """ switch buffer and execute cmd. then return the line number.
    """ not implemented 
    return 0
endfunction

" Try YCM and return location. many cause flush
function! TryYcmJumpAndReturnLocation(identifier)
    let pos = getpos('.')
    " if don't set pos[0], the bufnr is always 0.
    let pos[0] = bufnr() 
    silent! exec "YcmCompleter GoToDefinition ".a:identifier 
    if pos[0] == bufnr() && pos[1] == getpos('.')[1]
        return ["", -1, ""]
    else
        let filename = bufname(bufnr())
        let line_nr = getpos('.')[1]
        let text = getline('.')
        call setpos('.', pos)
        return [filename, line_nr, text]
    endif
endfun

function! AddTags(name)
endfun

function! UniverseCtrl()
    let under_cur = expand('<cfile>')
    let is_file = 0
    if match(under_cur, '[/\.]') != -1
        let is_file = 1
    endif
    if is_file 
        " jump to file 
        exec 'YcmComplete GoTo'
    else 
        call g:universe_searcher.search_and_render(expand("<cword>"), "")
    endif
endfunction

"------------
"  test case
"------------
if 0
    "let line_nr = PeekLineNumberFromSearch("/sss", "/void func")
    "call assert_true(line_nr, 24
    "let ret = GrepSearcher(s:searcher, "xk")
    "echo ret
    "call assert_true(line_nr, 24)
    "
    "
    "call TryYcmJumpAndReturnLocation("insert")
    "
    "
    let cur_s = s:searcher
    let ttt = cur_s.search("insert")
    call cur_s.render(ttt, "insert")

endif 
