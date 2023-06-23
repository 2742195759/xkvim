cd $HOME
wget http://10.255.125.22:8082/software/clangd.tar
tar -xf clangd.tar
apt update
apt install -y patchelf
cd ./clangd
bash ./init.sh
cat "export PATH=$PATH:$PATH:$HOME/clangd/" >> ~/.bashrc
source ~/.bashrc


