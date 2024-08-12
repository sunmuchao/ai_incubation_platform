#!/bin/bash
#跑之前注册plugins
line=$[$(cat -n /data/ContinuousIntegration/polars_test-benchmark/home/.polars_meta/polars.properties | grep 'polars.formula.plugins' | awk '{print $1}')]
str=$line""c" "polars.formula.plugins=[com.fanruan.polars.hihidata.data.formula.compiler.expression.function.plugin.HihidataPlugin]
sed -i "$str" /data/ContinuousIntegration/polars_test-benchmark/home/.polars_meta/polars.properties
line2=$[$(cat -n /data/ContinuousIntegration/polars_test-benchmark/home/.polars_meta/polars.properties | grep 'polars.formula.translator' | awk '{print $1}')]
str2=$line2""c" "polars.formula.translator=hihidata
sed -i "$str2" /data/ContinuousIntegration/polars_test-benchmark/home/.polars_meta/polars.properties
java -Xmx24G -Xms24G --add-exports java.base/jdk.internal.ref=ALL-UNNAMED -cp .:./libs/:./code/polars/polars-assembly/target/polars-assembly-1.0-SNAPSHOT.jar com.fanruan.polars.benchmark.cases.jsy.JSYQueryBenchMarkRunner /usr/banchMark/benchmark.properties

line=$[$(cat -n /data/ContinuousIntegration/polars_test-benchmark/home/.polars_meta/polars.properties | grep 'polars.formula.plugins' | awk '{print $1}')]
str=$line""c" "polars.formula.plugins=[com.fanruan.polars.formula.compiler.expression.function.PolarsCallFunctionPlugin,com.fanruan.polars.formula.compiler.expression.function.PolarsBuiltinFunctionPlugin]
sed -i "$str" /data/ContinuousIntegration/polars_test-benchmark/home/.polars_meta/polars.properties
line2=$[$(cat -n /data/ContinuousIntegration/polars_test-benchmark/home/.polars_meta/polars.properties | grep 'polars.formula.translator' | awk '{print $1}')]
str2=$line2""c" "polars.formula.translator=std
sed -i "$str2" /data/ContinuousIntegration/polars_test-benchmark/home/.polars_meta/polars.properties
java -Xmx24G -Xms24G -Dpolars.native.supported=false --add-exports java.base/jdk.internal.ref=ALL-UNNAMED -cp .:./libs/:./code/polars/polars-assembly/target/polars-assembly-1.0-SNAPSHOT.jar com.fanruan.polars.benchmark.cases.BenchmarkCaseRunner /usr/banchMark/benchmark_Customization.properties