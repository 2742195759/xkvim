git submodule update --init
cd chrome-web/Yiyan-Cli
git reset --hard HEAD
cd -
pip install -r $HOME/xkvim/requirement.txt
pip install -r $HOME/xkvim/xiongkun/plugin/pythonx/Xiongkun/rpc_server/requirements.txt
bash $HOME/xkvim/install_sh/install_clangd.sh
bash $HOME/xkvim/install_sh/install_chrome.sh
