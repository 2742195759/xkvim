# TODO: conda deactivate
~/xkvim/install.sh
cd ..
apt update
apt install libncurses-dev -y
git clone https://github.com/vim/vim.git
cd vim 
git pull
cd src
make distclean  # 如果您以前构建Vim
./configure --prefix=/usr --with-features=huge \
--enable-multibyte \
--enable-python3interp \
--with-python3-config-dir=`python3 ~/xkvim/find_pythonlib.py` \
--enable-cscope \
--enable-gui=auto \
--enable-gtk2-check \
--enable-fontset \
--enable-largefile \
--disable-netbeans \
--with-compiledby="xxx@email.com" \
--enable-fail-if-missing
/bin/rm -r /usr/share/vim/vim81
make install
make VIMRCLOC=/etc/vim/ VIMRUNTIMEDIR=/usr/share/vim MAKE="make -e -j 20"
ln -sf /usr/share/vim/vim82 /usr/share/vim/vim81
rm -rf /usr/bin/vim
source ~/.bashrc
