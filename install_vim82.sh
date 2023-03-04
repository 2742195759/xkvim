/root/miniconda3/bin/conda init
/root/miniconda3/bin/conda create -n vim python=3.9
conda activate vim

~/xkvim/install_sh/install_vim_config.sh
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
/bin/rm -rf /usr/share/vim/vim81
make install -j 20
make VIMRCLOC=/etc/vim/ VIMRUNTIMEDIR=/usr/share/vim MAKE="make -e -j 20"
ln -sf /usr/share/vim/vim82 /usr/share/vim/vim81
#rm -rf /usr/bin/vim
source ~/.bashrc
rm -f ~/xkvim/xiongkun/xiongkun
cp -f ~/xkvim/bash_scripts/vimdiff.sh /usr/bin/vimdiff
python3 -m pip install requests_toolbelt
python3 -m pip install easydict
# install coc dependences
./install_sh/install_coc_dep.sh
