start_command=$1

current_commit=`git fetch --all && git log develop --pretty=oneline |  head -n1 | cut -d' ' -f1`
upstream_lastest=`git fetch --all && git log origin/develop --pretty=oneline |  head -n1 | cut -d' ' -f1`
echo "Start command: $start_command in process $last_pid"
$start_command &
while true
do
    if [[ $upstream_lastest == $current_commit  ]]; then
        echo "Lastest. Just do nothing."
        sleep 10
    else
        # get the lastest version.
        git pull
        # kill all tcp_server.py
        ps | grep "python tcp_server.py" | cut -d' ' -f1 | xargs -n1 kill -9
        # sleep 30s to wait for socket to close()
        sleep 10
        $start_command &
    fi
done
