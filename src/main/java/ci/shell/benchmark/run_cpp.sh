#!/bin/bash
java -Dpolars.native.supported=true -cp polars-assembly-1.0-SNAPSHOT_cpp.jar com.fanruan.polars.benchmark.cases.jsy.JSYNativeQueryBenchMarkRunner /usr/banchMark/benchmark.properties