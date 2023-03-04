apt update
apt install -y git
git pull
ln -sf /root/xkvim/vimrc ~/.vimrc
ln -sf /root/xkvim/after ~/.vim/after
mkdir -p /tmp
mv ~/.vim/plugin/xiongkun /tmp/xiongkun.bak
ln -sf /root/xkvim/xiongkun ~/.vim/plugin/xiongkun

#if ( ll /root/bashrc_backup ); then
#else
    #echo "Backup bashrc in /root/bashrc_backup"
    #cp -rf /root/.bashrc /root/bashrc_backup
#fi

#rm -rf /root/.bashrc
rm -rf /root/.scripts
#ln -sf /root/xkvim/bashrc /root/.bashrc
#ln -sf /root/xkvim/bash_scripts /root/.scripts

echo "unset GREP_OPTIONS" >> /root/.bashrc
echo "export TERM=xterm-256color" >> /root/.bashrc
source /root/.bashrc

apt install -y python3-pip
pip3 install dict-cli

py_version=`python3 --version | cut -d ' ' -f 2 | cut -d '.' -f 1-2`
apt install -y python${py_version}-dev
apt install -y language-pack-zh-hans
python3 -m pip install requests
python3 -m pip install ply
# for clangd-index finder
wget -O /root/xkvim/cmd_script/clangd-index-finder http://10.255.125.22:8082/software/clangd-index-finder 
chmod +x /root/xkvim/cmd_script/clangd-index-finder

