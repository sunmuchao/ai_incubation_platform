#!/bin/bash

docker restart polars_test-benchmark && docker exec polars_test-benchmark /bin/bash -c 'java -Dpolars.extends.modules.class=com.fanruan.polars.hihidata.register.HihidataModuleRegister -cp .:./polars-assembly-1.0-SNAPSHOT.jar com.fanruan.polars.benchmark.cases.jsy.JSYBenchmarkUtils /usr/banchMark/home /usr/banchMark/suite /usr/banchMark/pls'