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
  let maxheight = get(a:opts, 'maxheight', 7)
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
        echo "sdfsdf"
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
    \ ["Jump YCM &definition", "YcmCompleter GoToDefinition"], 
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
    "let results = YCMSearcher(self, a:input_text)
    let results = []
    let results = results + CtagSearcher(self, a:input_text)
    let results = results + GrepSearcher(self, a:input_text)
    return results
endfunction

function! s:searcher.render(results, title)
    " unique
    " filter
    " render to boxlist
        " 1. first get the text and cmd.
        " 2. text is aligned by '\t'
    let to_render = [["id\tsource\tfilename\ttext\tother", ""]]
    let idx = 1
    for item in a:results
        let render_item = ["", ""]
        let render_item[0] = join([idx, item["source"], item["filename"], trim(item["text"]), trim(get(item, 'other', ''))], "\t")
        let render_item[1] = printf("call ExecuteJumpCmd('%s', '%s')", item.filename, item.cmd)
        call add(to_render, render_item)
        let idx += 1
    endfor 
    let self.hwnd = quickui#listbox#open(to_render, {'h': 20, 'title': a:title})
    let oldopt = popup_getoptions(self.hwnd.winid)
	let self.hwnd.old_filter = oldopt["filter"]
    let self.hwnd.old_callback = oldopt["callback"]
    let self.hwnd.raw = a:results
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
        let cur_selected = str2nr(@q) - 2
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
    return [{"filename": item[0], "lnum": item[1], "cmd": printf(":%d", item[1]), "other":"", "source":"YCM", "text":""}]

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
                let item = {'source': 'Grep'}
                let item.filename = bufname(qfitem.bufnr)
                let item.lnum = qfitem.lnum
                let item.text = qfitem.text
                let item.cmd  = printf(":%d", item.lnum)
                call add(ret, item)
            endif
        endfor
    endif
    return ret
endfunction

function! ExecuteJumpCmd(filename, cmd)
    silent exec "tabe ".a:filename
    silent exec a:cmd
endfunction

function! s:PeekLineNumber(universe_item)
    if get(a:universe_item, 'lnum', -1) != -1
        return a:universe_item['lnum']
    elseif a:universe_item['cmd'][0] == "/"
        return s:PeekLineNumberFromSearch(a:universe_item['filename'], a:universe_item['cmd'])
    else
        let cmd = hwnd.raw[cur_selected].cmd
        return 0
endfunction

function! s:PeekLineNumberFromSearch(filename, search_cmd)
    let new_buf = bufadd(a:filename)
    let lines = getbufline(new_buf, 1, '$')
    let line_nr = match(lines, a:search_cmd[1:-2]) + 1
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
    silent! exec "YcmCompleter GoToDefinition ".a:identifier 
    if pos[0] == getpos('.')[0] && pos[1] == getpos('.')[1]
        return ["", -1]
    else
        let filename = bufname(getpos('.')[0])
        let line_nr = getpos('.')[1]
        echo filename
        call setpos('.', pos)
        return [filename, line_nr]
    endif
endfun
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
