set nocompatible
set term=screen-256color
set rtp+=~/.vim/bundle/vundle/
set encoding=utf-8
call vundle#rc()

Bundle 'gmarik/vundle'
Bundle 'https://github.com/scrooloose/nerdtree'
Bundle 'taglist.vim'
Bundle 'https://github.com/honza/vim-snippets'
Bundle 'https://github.com/sirver/UltiSnips'
Bundle 'https://github.com/vim-airline/vim-airline'
Bundle 'https://github.com/kien/ctrlp.vim'
Bundle 'https://github.com/Raimondi/delimitMate'
Bundle 'https://github.com/tpope/vim-surround'
Bundle 'https://github.com/jreybert/vimagit'
Bundle 'https://github.com/AndrewRadev/quickpeek.vim'
Bundle 'https://github.com/skywind3000/vim-quickui'
Bundle 'https://github.com/tomasiser/vim-code-dark'
Bundle 'The-NERD-Commenter'
Bundle 'https://github.com/frazrepo/vim-rainbow'
Bundle 'https://github.com/neoclide/coc.nvim'
Bundle 'https://github.com/Yggdroot/indentLine'
Bundle 'https://github.com/github/copilot.vim'

if has("cscope")
  set cscopeprg=/usr/bin/cscope
  set csto=0
  set cst
  set nocsverb
  " add any database in current directory
  if filereadable("cscope.out")
      cs add cscope.out
  endif
  set csverb
endif

"nmap <C-@>a :cs find a <C-R>=expand("<cword>")<CR><CR>
nmap <C-\>s :cs find s <C-R>=expand("<cword>")<CR><CR>
nmap <C-\>g :cs find g <C-R>=expand("<cword>")<CR><CR>
nmap <C-\>c :cs find c <C-R>=expand("<cword>")<CR><CR>
nmap <C-\>t :cs find t <C-R>=expand("<cword>")<CR><CR>
nmap <C-\>e :cs find e <C-R>=expand("<cword>")<CR><CR>
nmap <C-\>f :cs find f <C-R>=expand("<cfile>")<CR><CR>
nmap <C-\>i :cs find i ^<C-R>=expand("<cfile>")<CR>$<CR>
nmap <C-\>d :cs find d <C-R>=expand("<cword>")<CR><CR>
nmap <F5> :NERDTreeToggle<cr>
nmap <F6> :TlistToggle<cr>

if has ("syntax")
  syntax on
endif

filetype detect

set autoindent
set ts=4
set expandtab
set shiftwidth=4
" 使用>> << 和 ctrl-T ctrl-D 0 ctrl-D 来缩进和反缩进
set nowrap
set hlsearch
set backspace=indent,eol,start whichwrap+=<,>,[,]

set ofu=syntaxcomplete#Complete


set mouse=

" option for foldmethod
set fdm=marker
set foldcolumn=2

"colorscheme molokai
colorscheme codedark
" xiongkun added in 2021 year
map gs :update<cr>
nn <up> <C-u>
nn <down> <C-d>
" nmap o  i<cr>
" options for delimitMate
let delimitMate_expand_cr = 1
let delimitMate_expand_space = 1

map <left> :tabp <cr>
map <right> :tabn <cr>
let g:ctrlp_working_path_mode = 'r'
set wildignore+=*/.git/*,*/.hg/*,*/.svn/*,*/build/*,*.pyc*,*.swp*,*.swo*,*/build_*/*      " Linux/MacOSX
set undofile
set undodir=/tmp/
set grepprg=egrep\ -n\ $*

let g:ctrlp_extensions = ['tag', 'line' ]
set scrolloff=8
set autoread
set autowrite
set mps+=<:>
set highlight=v:Error


" xiongkun defined function for cpp or python
fu! SelectAugment()
    " always exclusive; bacause we don't want to delete a argument
    let save_cursor = getcurpos()
    let save_register_s = getpos("'s")
    let save_register_e = getpos("'e")
    let start_cursor  = deepcopy(save_cursor)
    let end_cursor  = deepcopy(save_cursor)
    let [line, col] = searchpairpos('(', ',', ')', 'b')
    let start_cursor[1] = line 
    let start_cursor[2] = col 
    call setpos("'s", start_cursor)
    call setpos("." , save_cursor)
    let [line, col] = searchpairpos('(', ',', ')')
    let end_cursor[1] = line 
    let end_cursor[2] = col 
    call setpos("'e", end_cursor)
    normal! `slv`eh
    call setpos("'s", save_register_s)
    call setpos("'e", save_register_e)
endf

fu! SelectUnderlineWord()
    execute "keepjump normal! ?[^a-zA-Z]\r:nohlsearch\rlvN"
endf

" select a augment in functions: func(arg1, arg2, args4, call(123)) , when cursor in args1, select the args1
onoremap aa :<c-u>call SelectAugment()<cr>
" select a word between _. _first_second_third_ , if cursor in second, then select the second. 
onoremap au :<c-u>call SelectUnderlineWord()<cr>
" ugly here
nnoremap <space>e :<c-u>execute "normal!" "?{}\\\\|()\\\\|[]\r:nohlsearch\r" <cr> 


" Shot key for copy: disable the mouse and enable the mouse
cabbr vem set mouse=a
cabbr vdm set mouse=
cabbr vex <c-r>=expand('<cword>')<cr>


" Repace Operator, replace text with "0 register. (last yank)
nmap <silent> cr :set opfunc=CountSpaces<CR>g@
vmap <silent> <space>r :<C-U>call CountSpaces(visualmode(), 1)<CR>

function! CountSpaces(type, ...)
  let sel_save = &selection
  let &selection = "inclusive"
  let reg_save = @@

  if a:0  " Invoked from Visual mode, use gv command.
    silent exe "normal! gvd\"0P"
  elseif a:type == 'line'
    silent exe "normal! '[d']\"0Po\<esc>"
    "echom "Not Support LineWise for <space>r operator"
  else
    silent exe "normal! `[d`]x\"0P"
  endif

  let &selection = sel_save
  let @@ = reg_save
endfunction



""" Add () surround motion operator
nmap <silent> <space>b :set opfunc=SurroundWithBrace<CR>g@
vmap <silent> <space>b :<C-U>call SurroundWithBrace(visualmode(), 1)<CR>
function! SurroundWithBrace(type, ...)
  let sel_save = &selection
  let &selection = "inclusive"
  let reg_save = @@
  let old_s_pos = getpos("'s")
  let old_e_pos = getpos("'e")
  let start_pos = getpos("'[")
  let end_pos = getpos("']")
  call setpos("'s", start_pos)
  call setpos("'e", end_pos)

  if a:0  " Invoked from Visual mode, use gv command.
    echom "Not Support Visual Mode for <space>( operator"
    "silent exe "normal! gvd\"0P"
  elseif a:type == 'line'
    silent exe "normal! 'ea)\<esc>'si(\<esc>"
  else
    silent exe "normal! `ea)\<esc>`si(\<esc>"
  endif

  let &selection = sel_save
  let @@ = reg_save
  call setpos("'s", old_s_pos)
  call setpos("'e", old_e_pos)
endfunction

""" variable for ultisnips
let g:UltiSnipsExpandTrigger = '<c-j>'
let g:UltiSnipsJumpForwardTrigger='<c-j>'
let g:UltiSnipsJumpBackwardTrigger='<c-k>'

"""" YCM config
"let g:ycm_python_binary_path = '/usr/bin/python3'
"let g:ycm_server_python_interpreter = '/usr/bin/python2'

""" VimEnter
autocmd BufEnter * source ~/.vim/after/keymap.vim

if !(&diff)
    augroup NERDTREE
        autocmd!
        autocmd VimEnter * NERDTreeToggle | wincmd w
    augroup END
endif

if filereadable(expand("~/.xkconfig.vim"))
    autocmd VimEnter * source ~/.xkconfig.vim
endif

""" pdf for vim
abbre xkpdb breakpoint()
let mapleader='\'
set runtimepath+=$HOME/.vim/plugin/xiongkun/plugin
set shell=bash
set path+='./'
set cursorline
set tags+=$HOME/cpp_src/stl.tags


""" configure for quick-peek plugin 
let g:quickpeek_auto = v:true
set completeopt=menu,preview
" Open filetype plugin, you can use the quickpeek plugin
filetype plugin on 

""" configure for g:UltiSnippetEdit
let g:home=$HOME
let g:UltiSnipsSnippetStorageDirectoryForUltiSnipsEdit=g:home."/xkvim/xiongkun/plugin/UltiSnips/"

""" universe reflesh
function! UniverseReflesh()
    call UltiSnips#RefreshSnippets()
endfunction
nmap <F9> :call UniverseReflesh()<cr>
let g:ctrlp_by_filename = 1  "default by filename mode for speed."
nmap <leader><M-m> :tabe<cr>\M

let NERDTreeIgnore = ['\.pyc$', 'user_tag', '\.aux', '\.out', '\.log', '\.pdf']  " 过滤所有.pyc文件不显示
let g:netrw_ftp_list_cmd = "ls"
let g:netrw_ftp_cmd="ftp -p "

abbre fftp ftp://10.255.129.13:8081/

if !(&diff)
    " add branch information. 2022/5/19
    let g:airline_section_b = trim(system("git symbolic-ref --short HEAD"))
endif
set foldopen=hor,search,jump,block,mark,quickfix
set foldclose=all
hi CursorLine term=bold ctermbg=240
"hi CursorLine term=bold ctermbg=24 guibg=#13354A

function! MyPlugin(...)
    if &filetype == 'filefinder'
      let w:airline_section_a = 'FileFinder'
      let w:airline_section_b = getwinvar(winnr(), "filefinder_mode")
      let w:airline_section_c = getwinvar(winnr(), "filefinder_dir")
    endif
  endfunction
call airline#add_statusline_func('MyPlugin')
" Go to the last position.
" autocmd BufEnter * silent! normal! g`"zz
set noshowmode
set termwinscroll=10000000
let delimitMate_matchpairs = "(:),[:],{:}"
" set switchbuf=vsplit
let g:surround_no_mappings=1

hi TabLineSel term=reverse cterm=undercurl ctermfg=203 ctermbg=234 gui=undercurl guifg=#F44747 guibg=#1E1E1E guisp=#F44747


" rainbow plugin config:
" let g:rainbow_active = 1
set incsearch

source $HOME/xkvim/coc.vim
set nofoldenable


" paste and brakets
" http://stackoverflow.com/questions/5585129/pasting-code-into-terminal-window-into-vim-on-mac-os-x
" then https://coderwall.com/p/if9mda
" and then https://github.com/aaronjensen/vimfiles/blob/59a7019b1f2d08c70c28a41ef4e2612470ea0549/plugin/terminaltweaks.vim
" to fix the escape time problem with insert mode.
"
" Docs on bracketed paste mode:
" http://www.xfree86.org/current/ctlseqs.html
" Docs on mapping fast escape codes in vim
" http://vim.wikia.com/wiki/Mapping_fast_keycodes_in_terminal_Vim

if exists("g:loaded_bracketed_paste")
  finish
endif
let g:loaded_bracketed_paste = 1

let &t_ti .= "\<Esc>[?2004h"
let &t_te = "\e[?2004l" . &t_te


function! XTermPasteBegin(ret)
  set pastetoggle=<f29>
  set paste
  return a:ret
endfunction

execute "set <f28>=\<Esc>[200~"
execute "set <f29>=\<Esc>[201~"
map <expr> <f28> XTermPasteBegin("i")
imap <expr> <f28> XTermPasteBegin("")
vmap <expr> <f28> XTermPasteBegin("c")
cmap <f28> <nop>
cmap <f29> <nop>
tmap <f28> <nop>
tmap <f29> <nop>

" to avoid abandom
set hidden
