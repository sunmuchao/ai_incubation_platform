test=$(docker ps | grep polars_test-benchmark || true)
while [[ ! -z "$test" ]]
do
        echo "polars_test-benchmark is not empty !"
        sleep 1m
        test=$(docker ps | grep polars_test-benchmark || true)
done
java -jar /data/ContinuousIntegration/polars_test-benchmark/BenchMarkToDB.jar Dict
java -jar /data/ContinuousIntegration/polars_test-benchmark/BenchMarkToDB.jar Normal
