cd ..
apt update
apt install ctags -y

if [ -f $HOME/vim_dist.tar ]; then
    # Use the release version `vim_dist.tar` as vim 9.0
    # support python version is python3.8
    cd $HOME
    tar -xf vim_dist.tar
    cd vim
    ./init.sh
    conda create -n vim python=3.8
    echo 'export PATH=$HOME/vim:$PATH' >> $HOME/.bashrc
    echo 'export VIM=$HOME/vim/config/usr/share/vim' >> $HOME/.bashrc
    echo 'source activate vim'
    source ~/.bashrc
    cd $HOME
else
    # Install from source
    cd $HOME
    apt install libncurses-dev -y
    git clone https://github.com/vim/vim.git
    cd vim 
    git pull
    cd src
    make clean  # 如果您以前构建Vim
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
    make -j 20
    make install
    #make VIMRCLOC=/etc/vim/ VIMRUNTIMEDIR=/usr/share/vim MAKE="make -e -j 20"
    ln -sf /usr/share/vim/vim82 /usr/share/vim/vim81
    #cp -f ~/xkvim/bash_scripts/vimdiff.sh /usr/bin/vimdiff  # Circle vim bugs.
fi
    
~/xkvim/install_sh/install_vim_config.sh
git clone https://github.com/VundleVim/Vundle.vim.git ~/.vim/bundle/vundle

python3 -m pip install requests_toolbelt
python3 -m pip install easydict
python3 -m pip install ply
python3 -m pip install fuzzyfinder

vim -s ~/xkvim/install_sh/bundle_install.vim
# install coc dependences
cd $HOME/xkvim/
$HOME/xkvim/install_sh/install_coc_dep.sh
echo 'export PATH=$HOME/xkvim/cmd_script/:$PATH' >> $HOME/.bashrc
