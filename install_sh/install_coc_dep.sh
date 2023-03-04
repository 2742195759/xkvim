/root/xkvim/install_sh/install_node.sh
cd ~/.vim/bundle/coc.nvim/
npm install
yarn build
echo "coc.nvim:registry=http://mirrors.cloud.tencent.com/npm/" >> ~/.npmrc 

/root/miniconda3/bin/conda init
source /root/.bashrc
