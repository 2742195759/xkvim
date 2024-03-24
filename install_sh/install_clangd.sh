cd $HOME
wget https://github.com/clangd/clangd/releases/download/16.0.2/clangd-linux-16.0.2.zip
unzip clangd-linux-16.0.2.zip
rm clangd-linux-16.0.2.zip
echo "export PATH=$PATH:$PATH:$HOME/clangd_16.0.2/bin/" >> $HOME/.bashrc
