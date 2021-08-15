apt update
apt install -y git
git pull
ln -sf /root/xkvim/vimrc ~/.vimrc
ln -sf /root/xkvim/after ~/.vim/after
mkdir -p /tmp
mv ~/.vim/plugin/xiongkun /tmp/xiongkun.bak
ln -sf /root/xkvim/xiongkun ~/.vim/plugin/xiongkun
