"----------------------------------------------------------------------
" internal variables
"----------------------------------------------------------------------
"
"
""/home/data/ftp.py"
let s:searcher = {
\'user_item': {},
\'last': {},
\}
let s:previewer = {
\ 'winid': -1, 
\ 'bufid': -1, 
\}

let g:USE = s:searcher

function! s:TagPreviewOpen(arglist)
    call s:previewer.tag_atcursor(a:arglist[0])
endf
function! s:TagPreviewClose(arglist)
    call s:previewer.reset()
endf
let s:tag_preview_trigger= trigger#New(function("s:TagPreviewOpen"), function("s:TagPreviewClose"))


" Global Setting 
" g:jump_cmd   set the jump cmd, tabe | e | vertical e

let g:default_jump_cmd="e"
let g:enable_grep=1
let g:max_filename_length=35
let g:max_text_length=90
let g:enable_ycm=1
let g:enable_insert_preview=0

function! s:previewer.exec(cmd)
    if self.winid != 1
        call win_execute(self.winid, a:cmd)
    endif
endf

function! s:previewer.tag_atcursor(tags)
    call self.reset()

    " here we disable grep , because grep will cause screen flash. which 
    " is annoying
    "let g:enable_grep = 1
    let results = s:searcher.do_search(a:tags)

    "let userlist = get(s:searcher.user_item, a:tags, [])
    let userlist = results
    if len(userlist) == 0
        return 
    endif
    let opts = {'maxheight': 10, 
    \ 'col': 'cursor+30', 
    \ 'line': 'cursor+5', 
    \ 'minwidth': 0, 
    \ 'maxwidth': 10000,
    \ 'posinvert' : 1,
    \}
    call self.preview(userlist[0]['filename'], 
        \ userlist[0]['lnum'], 
        \ opts)
endf

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
  py3 Xiongkun.clangd_client._EndAutoCompile()
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
        \ 'minwidth':  get(a:opts,'minwidth',0),
        \ 'maxwidth':  get(a:opts,'maxwidth',10000),
        \ 'col':       a:opts.col,
        \ 'line':      a:opts.line,
        \ 'posinvert': get(a:opts,'posinvert',0),
        \ })
  silent let self.winid  = popup_create(bufnr, options)
  for setting in g:quickpeek_window_settings
    call win_execute(self.winid, 'silent setlocal '.setting)
  endfor
  call win_execute(self.winid, 'silent normal! '.a:linenr.'Gzz')
  py3 Xiongkun.clangd_client._StartAutoCompile()
endfunction
""}}}

let s:searcher.history = []
let s:searcher.status = {}
let s:searcher.is_preview = 0

let g:universe_searcher = s:searcher
let g:previewer = s:previewer

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
    \ ["&http server", "execute(':read /root/xkvim/template/http_server.py')"], 
    \ ["Jump File name", ""], 
    \ ["Jump Tag name", ""], 
    \ ["GoTo clangd &definition", "Def"], 
    \ ]
    call quickui#context#open(context, {})
endfunction

nmap U :call KeyworkSearch()<cr>

function! s:searcher.search_and_render(input_text, cwd)
    let ret = self.search(a:input_text)
    call self.render(ret, a:cwd, a:input_text)
endf

function! s:searcher.get_user_tag_path()
    let cwd = getcwd()
    let user_tag_path = cwd . "/user_tag"
    return user_tag_path
endf

function! s:searcher.Init()
    let file = self.get_user_tag_path()
    if filereadable(file) == 1 
        let self.user_item = ReadVariable(file)
    endif
endf

function! s:searcher.Exit()
    let file = self.get_user_tag_path()
    call SaveVariable(self.user_item, file)
endf

function! s:searcher.do_search(input_text)
    call CreateAndImportTmpTags()
    let results = []
    let results = results + UserSearcher(self, a:input_text)
    if g:enable_ycm==1
        let results = results + YCMSearcher(a:input_text)
    endif
    let results = results + CtagSearcher(a:input_text)
    if g:enable_grep==1
        let results = results + GrepSearcher(a:input_text)
    endif
    " [unique]
    let results = ResultsUnique(results)
    " [filter]
    let results = ResultsFilter(results)
    return results
endf

function! s:searcher.search(input_text)
    let results = self.do_search(a:input_text)
    " post-search
    call s:SetqfList(results)
    let self.last = {'input_text':a:input_text, 'results': results}
    return results
endfunction

function! s:StringTrimer(str, max_len)
    if a:max_len < len(a:str)
        return '|...' . a:str[-a:max_len:] . '|'
    else
        return '|' . a:str . '|'
    endif
endfunction

function! FilenameTrimer(filename)
    return s:StringTrimer(a:filename, g:max_filename_length)
endfunction

function! TextTrimer(text)
    if g:max_text_length < len(a:text)
        return a:text[0:g:max_text_length-1] . "..."
    else
        return a:text
    endif
endfunction

function! ResultsUnique(results)
    " remove the current postion.
    let current_key = fnamemodify(bufname(), ":p") . getpos('.')[1]
    let unique_set = {current_key: 1} 
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

function! ResultsFilter(results)
    let ignore_list = s:GetIgnoreList()
    call filter(a:results, function('s:IsIgnored', [ignore_list]))
    return a:results
endf

function! s:searcher.render(results, title, identifier)
    if len(a:results) == 0
        echoh Error
        echom "Not found: `". a:identifier . '`'
        echoh None
        return 
    endif
    " [render]
    "
    " render to boxlist
        " 1. first get the text and cmd.
        " 2. text is aligned by '\t'
    
    let to_render = []
    let idx = 1
    for item in a:results
        let render_item = ["", ""]
        let render_item[0] = join([idx, item["source"], trim(get(item, 'other', '')), FilenameTrimer(item["filename"]), TextTrimer(trim(item["text"]))], "\t")
        let render_item[1] = printf("call ExecuteJumpCmd('%s', '%s')", item.filename, escape(item.cmd, "'"))
        call add(to_render, render_item)
        let idx += 1
    endfor 
    let self.hwnd = quickui#listbox#open(to_render, {'h': 20, 'title': a:title, 'syntax': 'search'})
    silent call win_execute(self.hwnd.winid, printf("match Search /%s/", a:identifier))
    let oldopt = popup_getoptions(self.hwnd.winid)
	let self.hwnd.old_filter = oldopt["filter"]
    let self.hwnd.old_callback = oldopt["callback"]
    let self.hwnd.raw = a:results
    let oldopt.filter = function('s:CustomedKeyMap')
    let oldopt.callback = function('s:CustomedCallback')
    call popup_setoptions(self.hwnd.winid, oldopt)
endfunction

function s:PyWindowsKeyMap(winid, key)
    let key = a:key
    let keymap = py3eval("Xiongkun.vim_utils.GetKeyMap()")
    if get(keymap, a:key, "") != ""
        let key = keymap[a:key]
    endif
    if char2nr(a:key) == 0x80
        return 1
    endif
    return py3eval(printf('Xiongkun.BoxListWindowManager.on_key(%d, "%s")', a:winid, escape(key, '\"')))
endfunction

function s:PyWindowsCloseCallback(winid, code)
    return py3eval(printf('Xiongkun.BoxListWindowManager.on_close(%d, %d)', a:winid, a:code))
    return 0
endfunction

function SetWindowsCallBack(wid)
    let wid = a:wid
    let oldopt = popup_getoptions(wid)
    let oldopt.filter = function('s:PyWindowsKeyMap')
    let oldopt.callback = function('s:PyWindowsCloseCallback')
    call popup_setoptions(wid, oldopt)
endfunction

function SetWindowsCallBackWithDefault(wid)
    let wid = a:wid
    let oldopt = popup_getoptions(wid)
    let oldopt.filter = function('s:PyWindowsKeyMap', [oldopt.filter])
    let oldopt.callback = function('s:PyWindowsCloseCallback', [oldopt.callback])
    call popup_setoptions(wid, oldopt)
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
    if info == {}
        return {}
    endif
    let ret = {}
    let ret.col = info.col
    let ret.line = info.line + info.height
    let ret.minwidth = info.width
    let ret.maxwidth = info.width
    let ret.minheight = 9
    let ret.maxheight = 9
    return ret
endfunction

function! s:searcher.AddUserItem(pos_idx)
    " pos is a int
    let identifier = self.last.input_text
    let item = deepcopy(self.last.results[a:pos_idx])
    call remove(item, "source")
    let user_list = get(self.user_item,identifier,[])
    if index(user_list, item) == -1
        call add(user_list, item)
    endif
    let self.user_item[identifier] = user_list
endf

function! s:searcher.DelUserItem(pos_idx)
    let identifier = self.last.input_text
    let item = deepcopy(self.last.results[a:pos_idx])
    call remove(item, "source")
    let user_list = get(self.user_item,identifier,[])
    let idx = index(user_list, item)
    if idx != -1
        call remove(user_list, idx)
    endif
    let self.user_item[identifier] = user_list
endf

function! s:CustomedKeyMap(winid, key)
	let local = quickui#core#popup_local(a:winid)
	let hwnd = local.hwnd
    let OldFunc = hwnd.old_filter
    call win_execute(a:winid, "silent let @q=line('.')")
    let before_pos = str2nr(@q) - 1

    " control of user tag {{{
    if a:key == 'd'
        echoh Question
        echom "Set current item as definition"
        call s:searcher.AddUserItem(before_pos)
        echoh None
        return 1
    endif
    if a:key == 'D'
        echoh Question
        echom "Delete current item in user_definition"
        call s:searcher.DelUserItem(before_pos)
        echoh None
        return 1
    endif
    " }}}
    
    " Control of other jump cmd, {{{
    " such as "t" for tag jump, "s" for split, "v" for vertical
    if a:key == "t" || a:key == "s" || a:key == "v" || a:key == "z"
        let saved_jumpcmd = g:default_jump_cmd
        let CMD = { 's': 'sp ', 'v': 'vertical split ', 't': "tabe " , 'z': "pedit" }
        let g:default_jump_cmd = CMD[a:key]
        call s:searcher.DelUserItem(before_pos)
        let tmp_ret = popup_filter_menu(a:winid, "\<Enter>")
        let g:default_jump_cmd = saved_jumpcmd
        return tmp_ret
    endif
    " }}}
    
    """ Control the previewer  {{{
    if a:key == "\<UP>"
        call s:previewer.exec("normal \<c-u>")
        return 1
    endif
    if a:key == "\<DOWN>"
        call s:previewer.exec("normal \<c-d>")
        return 1
    endif
    """ }}}
    
    let ret = OldFunc(a:winid, a:key)

    " after call old filter {{{
    if a:key == "p"
        call s:searcher.preview_toggle()
    endif

    if s:searcher.is_preview == 1
        call win_execute(a:winid, "silent let @q=line('.')")
        let cur_selected = str2nr(@q) - 1
        let filename = hwnd.raw[cur_selected].filename
        let linenr = s:PeekLineNumber(hwnd.raw[cur_selected])
        let opts = s:GetPreviewRectangle(a:winid)
        if opts != {}
            call s:previewer.preview(filename, linenr, opts)
        endif
    endif
    " }}}
    return ret
endfunction

function! UserSearcher(searcher, input_text)
    let results = deepcopy(get(a:searcher.user_item, a:input_text, []))
    for item in results
        let item['source'] = 'User'
    endfor
    return results
endfunction

function! CtagSearcher(input_text)
    if a:input_text=="" | return[] | endif
    let items = taglist(a:input_text)
    " filter the partial match, exact match is valid
    let items = filter(items, "v:val['name'] == a:input_text")
    for item in items
        let item["source"] = "CTag"
        let item["other"]  = item.kind
        let item["text"]  =  trim(item.cmd, "\\/^$ \t")
        let item.text = substitute(item.text, "&", "&&", "g")
    endfor
    return items
endfunction

function! CtrlPSearcher(searcher, input_text)
endfunction

function! GrepSearcher(input_text)
    let pattern = (a:input_text)
    call SilentGrep(pattern)
    let qflist = getqflist()	
    let ret = []
    if len(qflist) > 0
        for qfitem in qflist
            if qfitem.valid
                let item = {'source': 'Grep', "other":""}
                let item.filename = bufname(qfitem.bufnr)
                let item.lnum = qfitem.lnum
                " to avoid the \t and &
                let item.text = tr(qfitem.text, "\t", " ") 
                let item.text = substitute(item.text, "&", "&&", "g")
                let item.cmd  = printf(":%d", item.lnum)
                call add(ret, item)
            endif
        endfor
    endif
    return ret
endfunction

function! EscapseSearchCmd(cmd)
    return escape(a:cmd, "~*.[]")
endfunction

function! ExecuteJumpCmd(filename, cmd)
    let new_tag_items = [{'bufnr': bufnr(), 'from': getpos('.'), 'matchnr': 0, 'tagname': getline('.')}]
    call settagstack(winnr(), {"items": new_tag_items}, 'a')
    let cmd = EscapseSearchCmd(a:cmd)
    silent exec printf("%s %s",g:default_jump_cmd, fnameescape(a:filename))
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
    let search_cmd = EscapseSearchCmd(a:search_cmd)
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

function! UniverseCtrl()
    let pattern = '\<'.expand("<cword>").'\>'
    execute printf("py3 Xiongkun.UniverseSearchEngine.singleton().search(\"%s\", \"%s\")", escape(pattern, "\\\"'"), g:nerd_search_path)
    execute "py3 Xiongkun.UniverseSearchEngine.singleton().render()"
endfunction

function! UniverseSearch()
    echoh Question
    echom "Search path : " . g:nerd_search_path . "    use `S` in nerdtree to change path"
    echoh None
    let input_text = trim(input("US>>>"))
    " bacause ycm can only search a tag in current cursor, so disable it.
    let g:enable_ycm=0 
    execute printf("py3 Xiongkun.UniverseSearchEngine.singleton().search(\"%s\", \"%s\", [0,1,0,0,1])", escape(input_text, "\\\"'"), g:nerd_search_path)
    execute "py3 Xiongkun.UniverseSearchEngine.singleton().render()"
    let g:enable_ycm=1
endfunction
"
" search for the function tag to preview while inserting. 
" find the first not matched function
"
function! SearchFunctionWhileInsert()
    if trim(getline('.')) == ""
        return
    endif
    let cur_pos = getcurpos()
    exec "normal [("
    let new_pos = getcurpos()
    let char = getline(".")[new_pos[2] - 1]
    if cur_pos[2] - 1 != new_pos[2] || char == "("
      exec "normal b"
      let tag = expand("<cword>")
    endif 
    "echom tag
    execute "py3 Xiongkun.GlobalPreviewWindow.find(\"".tag."\")"
    call setpos('.', cur_pos)
endfunction

function! TagPreviewTrigger() 
    call s:tag_preview_trigger.Trigger([expand("<cword>")])
endf
