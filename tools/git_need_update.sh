start_command=$1

current_commit=`git fetch --all && git log --pretty=oneline |  head -n1 | cut -d' ' -f1`
upstream_lastest=`git fetch --all && git log origin/develop --pretty=oneline |  head -n1 | cut -d' ' -f1`
echo "Start command: $start_command in process $last_pid"
$start_command &
while true
do
    git fetch --all
    current_commit=`git log --pretty=oneline |  head -n1 | cut -d' ' -f1`
    upstream_lastest=`git log origin/develop --pretty=oneline |  head -n1 | cut -d' ' -f1`
    if [[ $upstream_lastest == $current_commit  ]]; then
        echo "Lastest. Just do nothing."
        sleep 60
    else
        # get the lastest version.
        echo "Start fetch and update version. "
        git pull
        git checkout develop
        # kill all tcp_server.py
        ps | grep "python" | cut -d' ' -f1 | xargs -n1 kill -9
        # sleep 30s to wait for socket to close()
        sleep 120
        $start_command &
    fi
done
