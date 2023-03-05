$HOME/xkvim/install_sh/install_node.sh
cd ~/.vim/bundle/coc.nvim/
npm install
yarn build
echo "coc.nvim:registry=http://mirrors.cloud.tencent.com/npm/" >> ~/.npmrc 
source $HOME/.bashrc
vim -s $HOME/xkvim/install_sh/install_server.vim
