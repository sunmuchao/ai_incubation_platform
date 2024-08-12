#!/bin/bash
set -x
containerName=$1
docker restart $containerName && docker exec $containerName /bin/bash -c '/usr/lib/foundationdb/fdbmonitor --conffile /etc/foundationdb/foundationdb.conf --lockfile /var/run/fdbmonitor.pid --daemonize && mvn -Pjsy -Pjdk11 clean package -Dmaven.test.skip=true' && docker stop $containerName