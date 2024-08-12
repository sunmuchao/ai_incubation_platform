package ci.benchMark;

import java.util.HashSet;
import java.util.Set;

/**
 * @author sunmuchao
 * @date 2024/4/25 10:24 上午
 */
//用于填充结果集合，供展示使用
//只做填充，不做处理
public class BenchmarkResultSet {
    static Set<BenchmarkResultComponent> brcs = new HashSet<>();

    private static Set<BenchmarkResultComponent2> AllPerformanceRiseCase;
    private static Set<BenchmarkResultComponent2> AllPerformanceReduceCase;
    private static Set<BenchmarkResultComponent2> AllPerformanceFailCase;
    private static Set<BenchmarkResultComponent2> AllNewAddedCase;


    public static void fillBrc(BenchmarkResultComponent brc) {
        if (brcs.contains(brc)) {
            brcs.remove(brc);
            brcs.add(brc);
        } else {
            brcs.add(brc);
        }
    }

    public static Set<BenchmarkResultComponent> getBrcs() {
        return brcs;
    }

    public static void setAllPerformanceRiseCase(Set<BenchmarkResultComponent2> AllPerformanceRiseCase1) {
        AllPerformanceRiseCase = AllPerformanceRiseCase1;
    }

    public static Set<BenchmarkResultComponent2> getAllPerformanceRiseCase() {
        return AllPerformanceRiseCase;
    }

    public static Set<BenchmarkResultComponent2> getAllPerformanceReduceCase() {
        return AllPerformanceReduceCase;
    }

    public static Set<BenchmarkResultComponent2> getAllNewAddedCase() {
        return AllNewAddedCase;
    }


    public static void setAllPerformanceReduceCase(Set<BenchmarkResultComponent2> allPerformanceReduceCase) {
        AllPerformanceReduceCase = allPerformanceReduceCase;
    }

    public static Set<BenchmarkResultComponent2> getAllPerformanceFailCase() {
        return AllPerformanceFailCase;
    }

    public static void setAllPerformanceFailCase(Set<BenchmarkResultComponent2> allPerformanceFailCase) {
        AllPerformanceFailCase = allPerformanceFailCase;
    }

    public static void setAllNewAddedCase(Set<BenchmarkResultComponent2> allNewAddedCase) {
        allNewAddedCase = allNewAddedCase;
    }
}
