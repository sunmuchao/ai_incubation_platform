#!/bin/bash
jobName=$1
uuid=$2
workerpath=$3
number=$4
isContainBIChange=$5
branch=$6
filename=$workerpath$uuid"_"$jobName"_"$number".txt"
if [[ "$isContainBIChange" = "true" ]] && [[ "$branch" != "stable/jsy" ]]; then
    Dtest="/usr/lib/foundationdb/fdbmonitor --conffile /etc/foundationdb/foundationdb.conf --lockfile /var/run/fdbmonitor.pid --daemonize && mvn -Pbi -Pjdk11 clean test -Dspecial.scope=compile -Dtest="
else
    Dtest="/usr/lib/foundationdb/fdbmonitor --conffile /etc/foundationdb/foundationdb.conf --lockfile /var/run/fdbmonitor.pid --daemonize && mvn -Pjdk11 clean test -Dtest="
fi

if [ -e "$filename" ]; then
    # 读取文件内容，并按逗号分割成数组
    IFS=, read -ra content < "$filename"

    # 遍历数组中的元素
    for item in "${content[@]}"; do
	if [[ "$item" == *.* ]]; then
            # 如果item以.结尾，则在末尾加上**
            item="$item**"
        fi
	Dtest=$Dtest$item","
    done
else
    echo "File $filename not found."
fi
Dtest=$Dtest" -Dmaven.test.failure.ignore=true -DfailIfNoTests=false"
echo $Dtest
length=${#Dtest}
echo "Length of the Dtest is: $length"
docker restart $jobName && docker exec $jobName /bin/bash -c "$Dtest" && docker exec $jobName /bin/bash -c 'cd /tmp && rm -rf ./*' && docker stop $jobName