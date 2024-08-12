#!/bin/bash
set -x
containerName=$1
isOnlyHihidataChange=$2
cat>jsy.txt<<EOF
        <dependency>
            <groupId>com.fanruan.polars</groupId>
            <artifactId>polars-hihidata</artifactId>
            <version>\${project.version}</version>
        </dependency>
EOF
let line=$(cat -n ./polars-assembly/pom.xml | grep 'polars-native' |awk '{print $1}')+2
str=$line" "r" "jsy.txt
sed -i "$str" ./polars-assembly/pom.xml
sed -i 's/<testFailureIgnore>false/<testFailureIgnore>true/g' ./pom.xml
docker restart $containerName
if [[ $isOnlyHihidataChange == "false" ]]; then
        #docker restart polarsTestRelease && docker exec polarsTestRelease /bin/bash -c '/usr/lib/foundationdb/fdbmonitor --conffile /etc/foundationdb/foundationdb.conf --lockfile /var/run/fdbmonitor.pid --daemonize && mvn clean package -Dmaven.test.skip=true && mvn test surefire-report:report site -Dmaven.test.failure.ignore=true -DthreadCount=2 -DforkMode=always'
        #docker restart polarsTestRelease && docker exec polarsTestRelease /bin/bash -c '/usr/lib/foundationdb/fdbmonitor --conffile /etc/foundationdb/foundationdb.conf --lockfile /var/run/fdbmonitor.pid --daemonize && mvn clean package -Dmaven.test.skip=true && mvn test surefire-report:report site -Dtest=PruneColumnsTest#testPruneWindow  -DfailIfNoTests=false -Dmaven.test.failure.ignore=true'
        docker exec $containerName /bin/bash -c '/usr/lib/foundationdb/fdbmonitor --conffile /etc/foundationdb/foundationdb.conf --lockfile /var/run/fdbmonitor.pid --daemonize && mvn clean package -Dmaven.test.skip=true && mvn -Pjdk11 test surefire-report:report site -Dmaven.test.failure.ignore=true'
elif [[ $isOnlyHihidataChange == "true" ]];then
        docker exec $containerName /bin/bash -c '/usr/lib/foundationdb/fdbmonitor --conffile /etc/foundationdb/foundationdb.conf --lockfile /var/run/fdbmonitor.pid --daemonize && mvn clean package -Dmaven.test.skip=true && mvn -Pjdk11 test -pl polars-hihidata surefire-report:report site -Dmaven.test.failure.ignore=true'
fi