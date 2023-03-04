apt update
apt install -y git
git pull
ln -sf /root/xkvim/vimrc ~/.vimrc
ln -sf /root/xkvim/after ~/.vim/after
mkdir -p /tmp
mv ~/.vim/plugin/xiongkun /tmp/xiongkun.bak
ln -sf /root/xkvim/xiongkun ~/.vim/plugin/xiongkun
rm -rf /root/.bashrc
rm -rf /root/.scripts
ln -sf /root/xkvim/bashrc /root/.bashrc
ln -sf /root/xkvim/bash_scripts /root/.scripts
source /root/.bashrc

apt install -y python3-pip
pip3 install dict-cli

apt install -y language-pack-zh-hans
python3 -m pip install requests
python3 -m pip install ply
# for clangd-index finder
wget -O /root/xkvim/cmd_script/clangd-index-finder http://10.255.125.22:8082/software/clangd-index-finder 
chmod +x /root/xkvim/cmd_script/clangd-index-finder

