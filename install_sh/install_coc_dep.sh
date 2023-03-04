./install_node.sh
cd ~/.vim/bundle/coc.nvim/
npm install
yarn build
echo "coc.nvim:registry=http://mirrors.cloud.tencent.com/npm/" >> ~/.npmrc 
