apt update
apt install -y git
git pull
ln -sf /root/xkvim/vimrc ~/.vimrc
mkdir -p /tmp
mv ~/.vim/plugin/xiongkun /tmp/xiongkun.bak
ln -sf /root/xkvim/xiongkun ~/.vim/plugin/xiongkun
