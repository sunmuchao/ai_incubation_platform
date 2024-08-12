#!/bin/bash
set -x
containerName=$1
docker restart $containerName
for i in {1..3}; do
    failures=$(docker exec $containerName /bin/bash -c "find . -type f -name '*.txt' -exec grep -H -e '<<< FAILURE' -e '<<< ERROR' {} \; | grep -v 'Errors:' | awk -F '[:()]' '{print \$3\"#\"\$2}' | uniq | tr '\n' ',' | sed 's/,$//'")
    if [ -n "$failures" ]; then
        Dtest="/usr/lib/foundationdb/fdbmonitor --conffile /etc/foundationdb/foundationdb.conf --lockfile /var/run/fdbmonitor.pid --daemonize && mvn -Pjdk11 -Dtest="
	Dtest=$Dtest$failures" test -Dmaven.test.failure.ignore=true -DfailIfNoTests=false"
        echo $Dtest
        docker exec $containerName /bin/bash -c "$Dtest"
    else
      echo "No test failures. Exiting."
      exit 0
    fi
done
docker stop $containerName