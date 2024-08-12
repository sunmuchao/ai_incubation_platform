#!/bin/bash


arr=$(grep "fallCaseList" /data/ContinuousIntegration/polars_test-benchmark/inject_variables.properties | awk -F "=" '{print $2;}' | awk -F "," '{for(i=1;i<=NF;i++){print $i;}}')
file=$(grep "csvPath" /data/ContinuousIntegration/polars_test-benchmark/benchmark.properties | awk -F "=/usr/banchMark/" '{print $2;}')

for fallCasePls in ${arr[*]}
do
        echo "在$file中删除$fallCasePls"
        sed -i '/'"$fallCasePls"'/d' /data/ContinuousIntegration/polars_test-benchmark/${file}
        #判断fallCase是jsy还是自定义的
        #if grep -q "$fallCasePls" /data/ContinuousIntegration/polars_test-benchmark/${customization_file}; then
                #说明性能下降的是自定义用例，需要将结果输入到file文件中
        #        echo "性能下降的casename:"$fallCasePls
        #else
        echo "将$fallCasePls 复制至pls_fallcase目录"
        cp /data/ContinuousIntegration/polars_test-benchmark/pls/$fallCasePls /data/ContinuousIntegration/polars_test-benchmark/pls_fallcase/
        #fi
done