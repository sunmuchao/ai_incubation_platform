#!/bin/bash
line=$[$(cat -n /usr/banchMark/home_dict/.polars_meta/polars.properties | grep 'polars.formula.plugins' | awk '{print $1}')]
str=$line""c" "polars.formula.plugins=[com.fanruan.polars.hihidata.data.formula.compiler.expression.function.plugin.HihidataPlugin]
sed -i "$str" /usr/banchMark/home_dict/.polars_meta/polars.properties
line2=$[$(cat -n /usr/banchMark/home_dict/.polars_meta/polars.properties | grep 'polars.formula.translator' | awk '{print $1}')]
str2=$line2""c" "polars.formula.translator=hihidata
sed -i "$str2" /usr/banchMark/home_dict/.polars_meta/polars.properties
java -Xmx24G -Xms24G -Dpolars.native.supported=false  --add-exports java.base/jdk.internal.ref=ALL-UNNAMED -cp .:./code/polars/polars-assembly/target/polars-assembly-1.0-SNAPSHOT.jar com.fanruan.polars.benchmark.cases.jsy.JSYQueryBenchMarkRunner /usr/banchMark/benchmark_fallcase.properties