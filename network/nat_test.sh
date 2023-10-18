cd ~/xkvim/tools/
./start_rpc.sh 20000 &
cd ~/xkvim/network/
python nat_server.py --port 30000 & 
python nat_client.py --input 0.0.0.0:30000 --output 0.0.0.0:20000 &

