package ci.benchMark;

import java.io.FileNotFoundException;
import java.util.Set;

/**
 * @author sunmuchao
 * @date 2024/4/28 4:32 下午
 */

//结果处理器: 用于对BenchmarkResultSet进行处理，供展示使用
public class BenchmarkResultProcessor {

    public void process() throws FileNotFoundException {
        Set<BenchmarkResultComponent> brcs = BenchmarkResultSet.getBrcs();
        BenchmarkResultSetProcessor brsp = new BenchmarkResultSetProcessor(brcs);
        brsp.process();
    }
}
