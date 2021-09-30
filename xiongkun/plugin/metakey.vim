"表示时间延迟。timeout和ttimeout,打开用来打开M-d映射。
"set ttimeout=on
"move AltKeyStart.vimrc to this file


set ttimeoutlen=15
set <M-e>=e  "表示结束
inoremap <M-e> <esc>
set <M-d>=d  "表示定义函数
set <M-;>=;  "补充分号
set <M-a>=a  "添加注释
set <M-A>=A  "取消注释
set <M-f>=f  "寻找定义，.h -> .cpp
set <M-s>=s  "定义Set和Get函数
set <M-1>=1  "切换tab , prev
set <M-2>=2  "切换tab , next 
set <M-o>=o  "Jump前一个
set <M-i>=i  "Jump后一个
set <M-F>=F  "切换Source/Head文件
set <M-m>=m  
set <M-W>=W 
"set <M->=  "换行，但是会执行
nnoremap  <M-o> <C-o>
nnoremap  <M-i> <C-i>

""" commandline map  {{{
cnoremap <M-a> <Home>
cnoremap <M-e> <End>
cnoremap <M-w> <C-w>
"""}}}
