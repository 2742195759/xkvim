# Not that: python install please exit the conda.
cd ~/
/bin/rm gdb-12.1.tar.xz
wget http://10.255.125.22:8082/software/gdb-12.1.tar.xz
tar -xf gdb-12.1.tar.xz
cd gdb-12.1/
mkdir build
cd build
apt update
apt install -y libncurses5-dev libpython-dev texinfo libgmp3-dev
../configure --with-python --enable-tui
make -j 48 
make install
