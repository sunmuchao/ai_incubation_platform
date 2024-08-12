package ci.benchMark;

import base.cmd.ShellTool;
import java.util.List;

/**
 * @author sunmuchao
 * @date 2023/12/1 10:09 上午
 */
//负责执行一条Benchmark用例，并将结果写入到数据库中
public class BenchMarkRunner {
    String runBenchmarkPath;
    String jobId;
    //String systemName;

    BenchMarkRunner(String benchmarkPath, String jobId) {
        this.runBenchmarkPath = benchmarkPath;
        //this.systemName = systemName;
        this.jobId = jobId;
    }

    //传递集合，集合可以包含1个用例、也可以包含N个用例
    public void run(List<String> cns) throws Exception {
        StringBuilder cnss = new StringBuilder();
        for(String cn : cns){
            cnss.append(cn + ",");
        }
        cnss = new StringBuilder(cnss.substring(0,cnss.length() - 1));
        //执行benchmark，支持超时限制，堆栈或dump打印等功能
        ShellTool.cmd("sh " + runBenchmarkPath + " " + jobId + " " + cnss);
    }
}
