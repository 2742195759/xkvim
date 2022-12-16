echo "Script:" $1
echo "StartCmd:" $2
#echo "Paddle:" $2
rm -rf /tmp/profile
rm -rf /tmp/profile.tar
mkdir /tmp/profile
cp /home/data/Paddle4/Paddle/build/python/dist/paddlepaddle_gpu-0.0.0-cp37-cp37m-linux_x86_64.whl /tmp/profile
echo $2 > /tmp/profile/start.sh
cp -r $1 /tmp/profile
find /tmp/profile/ -name 'output' | xargs -n1 rm -rf
find /tmp/profile/ -name 'build*' | xargs -n1 rm -rf
find /tmp/profile/ -name 'core.*' | xargs -n1 rm -rf
cd /tmp/
tar -cf profile.tar profile
unset http_proxy
unset https_proxy
du -hs /tmp/profile.tar
python3 ~/xkvim/cmd_script/upload.py --file profile.tar
#python3 ~/xkvim/cmd_script/converse_execute.py --name profile --cmd "cd /home/ssd3/ && bash /home/ssd3/start_profile.sh" 
