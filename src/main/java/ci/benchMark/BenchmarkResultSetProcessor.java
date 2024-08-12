package ci.benchMark;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * @author sunmuchao
 * @date 2024/4/29 3:28 下午
 */

//用于对BenchmarkResultSet结果集进行处理,
//例如提取我们认为三次均提升才算提升，最终是否提升的判断是在这层做的，这层用来对结果进行进一步处理，方便上层直接使用的
public class BenchmarkResultSetProcessor {
    List<String> allCaseNames;
    Set<BenchmarkResultComponent> brcs;

    BenchmarkResultSetProcessor(Set<BenchmarkResultComponent> brcs) {
        Set caseSet = new HashSet();
        for (BenchmarkResultComponent brc : brcs) {
            caseSet.add(brc.getCaseName());
        }

        allCaseNames = new ArrayList<>();
        allCaseNames.addAll(caseSet);
        this.brcs = brcs;
    }

    //对BenchmarkResultSet进行处理，让BenchmarkResultSet拥有各种结果类型集合
    public void process() {
        getAllPerformanceRiseCases();
        getAllPerformanceReduceCases();
        getAllPerformanceFailCases();
        getAllNewAddedCases();
    }

    private void getAllNewAddedCases() {
        Set<BenchmarkResultComponent2> newAddedList = new HashSet<>();
        for (String caseName : allCaseNames) {

            BenchmarkResultComponent2 brc2 = new BenchmarkResultComponent2(caseName);

            for (BenchmarkResultComponent brc : brcs) {
                if (caseName.equals(brc.getCaseName())) {
                    if (brc.isNewAdded != null) {
                        brc2.setA(brc.getA());
                        if (brc.isNewAdded) {
                            brc2.addBenchmarkResultItemToB(brc.getB());
                            newAddedList.add(brc2);
                        }
                    }
                }
            }
        }
        BenchmarkResultSet.setAllNewAddedCase(newAddedList);
    }

    public void getAllPerformanceRiseCases() {
        Set<BenchmarkResultComponent2> performanceRiseList = new HashSet<>();
        for (String caseName : allCaseNames) {
            int i = 0;

            BenchmarkResultComponent2 brc2 = new BenchmarkResultComponent2(caseName);

            for (BenchmarkResultComponent brc : brcs) {
                if (caseName.equals(brc.getCaseName())) {
                    if (brc.PerformanceRise != null) {
                        brc2.setA(brc.getA());
                        brc2.addBenchmarkResultItemToB(brc.getB());
                        if (brc.PerformanceRise) {
                            i++;
                        }
                    }
                }
            }
            if (i == 3) performanceRiseList.add(brc2);
        }

        BenchmarkResultSet.setAllPerformanceRiseCase(performanceRiseList);
    }

    public void getAllPerformanceReduceCases() {
        Set<BenchmarkResultComponent2> performanceReduceList = new HashSet<>();
        for (String caseName : allCaseNames) {

            BenchmarkResultComponent2 brc2 = new BenchmarkResultComponent2(caseName);

            for (BenchmarkResultComponent brc : brcs) {
                if (caseName.equals(brc.getCaseName())) {
                    if (brc.PerformanceReduce != null) {
                        brc2.setA(brc.getA());
                        if (brc.PerformanceReduce) {
                            brc2.addBenchmarkResultItemToB(brc.getB());
                            performanceReduceList.add(brc2);
                        }
                    }
                }
            }
        }
        BenchmarkResultSet.setAllPerformanceReduceCase(performanceReduceList);
    }

    public void getAllPerformanceFailCases() {
        Set<BenchmarkResultComponent2> performanceFailList = new HashSet<>();
        for (String caseName : allCaseNames) {

            BenchmarkResultComponent2 brc2 = new BenchmarkResultComponent2(caseName);

            for (BenchmarkResultComponent brc : brcs) {
                if (caseName.equals(brc.getCaseName())) {
                    if (brc.fail != null) {
                        brc2.setA(brc.getA());
                        if (brc.fail) {
                            brc2.addBenchmarkResultItemToB(brc.getB());
                            performanceFailList.add(brc2);
                        }
                    }
                }
            }
        }
        BenchmarkResultSet.setAllPerformanceFailCase(performanceFailList);
    }
}
