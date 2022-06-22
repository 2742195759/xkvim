"表示时间延迟。timeout和ttimeout,打开用来打开M-d映射。
"set ttimeout=on
"move AltKeyStart.vimrc to this file


set ttimeoutlen=15
set <M-e>=e  "表示结束
inoremap <M-e> <esc>
set <M-d>=d  "表示定义函数
set <M-r>=r  "表示定义函数
set <M-;>=;  "补充分号
set <M-a>=a  "添加注释
set <M-A>=A  "取消注释
set <M-f>=f  "寻找定义，.h -> .cpp
set <M-s>=s  "定义Set和Get函数
set <M-c>=c  "寻找到Decl of cpp
set <M-1>=1  "切换tab , prev
set <M-2>=2  "切换tab , next 
set <M-o>=o  "Jump前一个
set <M-u>=u  "open preview window in pre windows.
set <M-i>=i  "Jump后一个
set <M-F>=F  "切换Source/Head文件
set <M-m>=m  "GoTo the Git Commit
set <M-W>=W 
set <M-w>=w 
set <M-p>=p  "preview popup window.
set <M-j>=j  "next Index search results.
set <M-k>=k  "prev Index search results.
set <M-e>=e  "<ESC>"
set <M-/>=/  "<ESC>"
"set <M->=  "换行，但是会执行
nnoremap  <M-o> <C-o>zv
nnoremap  <M-i> <C-i>zv

""" commandline map  {{{
cnoremap <M-a> <Home>
cnoremap <M-e> <End>
cnoremap <M-w> <C-w>
"""}}}

noremap <F4> :redraw!<cr>
noremap <M-d> :Def<cr>
noremap <M-r> :Ref<cr>
noremap <M-c> 10[{

" 因为meta key 存在的原因，原来的 esc 就是 会导致 esc 出现延迟，所以使用
" <M-e> 作为 esc ，保持输入的流畅性。这样的实现很舒服。我觉得可以。
" 所有的按钮不应该使用 <M-e>
inoremap <M-e> <esc>
cnoremap <M-e> <C-c>
nnoremap <M-e> <esc>
vnoremap <M-e> <esc>
