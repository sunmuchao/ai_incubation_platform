package ci.benchMark;

import java.util.List;

/**
 * @author sunmuchao
 * @date 2024/4/24 4:49 下午
 */

//比较处理器：完成所有用例的处理,并对结果进行处理
public class BenchmarkCompareProcessor {
    private BenchmarkForm bf;
    private List<String> allCaseNames;

    BenchmarkCompareProcessor(BenchmarkForm bf, List<String> allCaseNames){
        this.bf = bf;
        this.allCaseNames = allCaseNames;
    }

    public void process() throws Exception {
        for(String caseName : allCaseNames){
            //比较执行器：完成单一用例的所有组合动作
            BenchmarkCompareActuator bca = new BenchmarkCompareActuator(caseName);
            //比较性能变动
            bca.performanceChanges(bf);
            //竞品对比，例如polars对比sr
            bca.competitorContrast(bf);
        }

        //对结果进行处理
        BenchmarkResultProcessor brp = new BenchmarkResultProcessor();
        brp.process();
    }
}
