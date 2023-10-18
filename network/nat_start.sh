cd ~/xkvim/tools/
./start_rpc.sh 10010 &
cd ~/xkvim/network/
python nat_client.py --input $1 --output 0.0.0.0:10010
