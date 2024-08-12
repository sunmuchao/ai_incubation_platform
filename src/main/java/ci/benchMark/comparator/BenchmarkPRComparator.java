package ci.benchMark.comparator;

import ci.benchMark.BenchmarkComparateOpertor;

/**
 * @author sunmuchao
 * @date 2024/4/26 3:27 下午
 */
public class BenchmarkPRComparator implements BenchmarkComparator {
    private String caseName;

    public BenchmarkPRComparator(String caseName){
        this.caseName = caseName;
    }

    @Override
    public void compare(String A, String B) {
    }

    public void performanceRise(String A, String B){
        BenchmarkComparateOpertor bco = new BenchmarkComparateOpertor();
        bco.performanceRise(A, B, caseName);
    }

    public void performanceReduce(String A, String B){
        BenchmarkComparateOpertor bco = new BenchmarkComparateOpertor();
        bco.performanceReduce(A, B, caseName);
    }

    public void performancefail(String A){
        BenchmarkComparateOpertor bco = new BenchmarkComparateOpertor();
        bco.performancefail(A, caseName);
    }

    public void addedCases(String A,String B) {
        BenchmarkComparateOpertor bco = new BenchmarkComparateOpertor();
        bco.addedCases(A, B, caseName);
    }
}
