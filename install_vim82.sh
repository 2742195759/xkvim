cd ..
apt update
apt install ncursorlib-dev -y
git clone https://github.com/vim/vim.git
cd vim 
git pull
cd src
make distclean  # 如果您以前构建Vim
./configure --with-features=huge \
--enable-multibyte \
--enable-pythoninterp=dynamic \
--with-python-config-dir=/usr/lib/python2.7/config-x86_64-linux-gnu \
--enable-python3interp=dynamic \
--with-python3-config-dir=/usr/lib/python3.6/config-3.6m-x86_64-linux-gnu \
--enable-cscope \
--enable-gui=auto \
--enable-gtk2-check \
--enable-fontset \
--enable-largefile \
--disable-netbeans \
--with-compiledby="xxx@email.com" \
--enable-fail-if-missing \
--prefix=/usr/local 
make -j 20
make install
apt remove vim
