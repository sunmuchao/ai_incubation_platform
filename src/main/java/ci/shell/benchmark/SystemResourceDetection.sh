#!/bin/bash
set -x

#检测环境性能
loadAvg=$(uptime | awk '{print $11}')
loadAvg=${loadAvg%?}
loadAvg=$(echo $loadAvg | awk '{print int($0)}')
while [ $loadAvg -ge 2 ]
do
   sleep 1m
   echo "sleep 1m"
   loadAvg=$(uptime | awk '{print $11}')
   loadAvg=${loadAvg%?}
   loadAvg=$(echo $loadAvg | awk '{print int($0)}')
done

#磁盘IO，最近60s内平均利用率
loadDisk=$(iostat -d -x /dev/sda1 30 2 | awk 'NR == 8{print $23}')
loadDisk=${loadDisk%?}
loadDisk=$(echo $loadDisk | awk '{print int($0)}')

while [[ $loadDisk -ge 5 ]]
do
        sleep 1m
        echo "sleep 1m"
        loadDisk=$(iostat -d -x /dev/sda1 30 2 | awk 'NR == 8{print $23}')
        echo $loadDisk
        loadDisk=${loadDisk%?}
        loadDisk=$(echo $loadDisk | awk '{print int($0)}')
        echo $loadDisk
done