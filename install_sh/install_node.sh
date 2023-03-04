wget -c https://nodejs.org/download/release/v15.14.0/node-v15.14.0-linux-x64.tar.xz
rm -rf node-v15.14.0-linux-x64/ && tar -xf node-v15.14.0-linux-x64.tar.xz
echo 'export PATH=$PATH:/root/xkvim/node-v15.14.0-linux-x64/bin' >> ~/.bashrc
export PATH=$PATH:/root/xkvim/node-v15.14.0-linux-x64/bin
npm config set registry http://mirrors.cloud.tencent.com/npm/
npm install --global n
n install v17.9.1
npm install --global yarn
