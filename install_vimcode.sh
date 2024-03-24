apt install -y wget
os_arch=`python3 find_platform.py`
if [ $os_arch == "Linux_aarch" ]; then
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh -O Miniconda3.sh
fi
if [ $os_arch == "Linux_x86" ]; then
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O Miniconda3.sh
fi
bash Miniconda3.sh
git submodule update --init
cd chrome-web/Yiyan-Cli
git reset --hard HEAD
cd -
pip install -r $HOME/xkvim/requirement.txt
pip install -r $HOME/xkvim/xiongkun/plugin/pythonx/Xiongkun/rpc_server/requirements.txt
bash $HOME/xkvim/install_sh/install_clangd.sh
bash $HOME/xkvim/install_sh/install_chrome.sh
