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
