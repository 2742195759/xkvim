set nocompatible

set rtp+=~/.vim/bundle/vundle/
set encoding=utf-8
call vundle#rc()

Bundle 'gmarik/vundle'
Bundle 'https://github.com/scrooloose/nerdtree'
Bundle 'taglist.vim'
Bundle 'https://github.com/honza/vim-snippets'
Bundle 'https://github.com/sirver/UltiSnips'
Bundle 'https://github.com/Shougo/neocomplete.vim'
Bundle 'https://github.com/tomasr/molokai'
Bundle 'https://github.com/vim-airline/vim-airline'
Bundle 'https://github.com/kien/ctrlp.vim'
Bundle 'https://github.com/Valloric/YouCompleteMe'
Bundle 'https://github.com/Raimondi/delimitMate'
Bundle 'https://github.com/tpope/vim-surround'
Bundle 'https://github.com/jreybert/vimagit'
Bundle 'https://github.com/AndrewRadev/quickpeek.vim'
Bundle 'https://github.com/skywind3000/vim-quickui'
Bundle 'The-NERD-Commenter'


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
set foldcolumn=1

colorscheme molokai
"source ~/Important/MyVim/_MY_VIM_/AltKeyStart.vimrc  # move to metakey.vim
source ~/Important/MyVim/_MY_VIM_/WindowTabeSwitch.vimrc
if (or(&filetype == 'c',&filetype=='cpp'))
	source ~/Important/MyVim/_MY_VIM_/VimCpp.vimrc
elseif (&filetype == 'vim')
	set commentstring=\"%s
elseif (&filetype == 'python')
    set commentstring=#%s
    source ~/Important/MyVim/_MY_VIM_/VimPython.vimrc
end

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

""" YCM config
let g:ycm_python_binary_path = '/usr/bin/python3'

""" VimEnter
autocmd BufEnter * source ~/.vim/after/keymap.vim

augroup NERDTREE
    autocmd!
    autocmd VimEnter * NERDTreeToggle | wincmd w
augroup END

if filereadable(expand("~/.xkconfig.vim"))
    autocmd VimEnter * source ~/.xkconfig.vim
endif
"""Add YCM jump abbre
cabbre yd YcmCompleter GoToDefinition
cabbre yt YcmCompleter GetType
cabbre yp YcmCompleter GetParent
cabbre yi YcmCompleter GoToInclude
cabbre yf YcmCompleter FixIt
cabbre yr YcmCompleter GoToReference

""" pdf for vim
abbre xkpdb import pdb<cr>pdb.set_trace()
let mapleader='\'
set runtimepath+=/root/.vim/plugin/xiongkun/plugin
set shell=bash
set path+='./'
set cursorline
set tags+=/root/cpp_src/stl.tags
hi CursorLine cterm=Underline ctermbg=None ctermfg=None



""" configure for quick-peek plugin 
let g:quickpeek_auto = v:true
set completeopt=menu,preview
" Open filetype plugin, you can use the quickpeek plugin
filetype plugin on 

""" configure for g:UltiSnippetEdit
let g:UltiSnipsSnippetStorageDirectoryForUltiSnipsEdit="/root/xkvim/xiongkun/plugin/UltiSnips/"

""" universe reflesh
function! UniverseReflesh()
    call UltiSnips#RefreshSnippets()
    YcmRestartServer
endfunction
nmap <F9> :call UniverseReflesh()<cr>
let g:ctrlp_by_filename = 1  "default by filename mode for speed."
nmap <leader><M-m> :tabe<cr>\M
