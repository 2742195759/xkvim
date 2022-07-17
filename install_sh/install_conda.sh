wget http://10.255.125.22:8082/software/Miniconda3-latest-Linux-x86_64.sh
rm -rf /root/miniconda3
bash ./Miniconda3-latest-Linux-x86_64.sh
eval "$(/root/miniconda3/bin/conda shell.bash hook)"
source ~/.bashrc
conda create -n paddle python==3.7
conda activate paddle
python -m pip install paddlepaddle-gpu==2.3.1 -i https://mirror.baidu.com/pypi/simple
