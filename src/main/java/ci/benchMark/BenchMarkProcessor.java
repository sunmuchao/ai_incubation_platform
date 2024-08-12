package ci.benchMark;

import java.nio.file.Path;
import java.util.List;

/**
 * @author sunmuchao
 * @date 2023/11/23 2:46 下午
 */
//负责将所有用例传递给BenchMarkRunner
public class BenchMarkProcessor {
    private String runBenchmarkPath;
    private String systemName;
    private String jobId;

    BenchMarkProcessor(String category, String systemName, Path workPath, String jobId) {
        this.systemName = systemName;
        this.runBenchmarkPath = getRunBenchmark(category, systemName, workPath);
        this.jobId = jobId;
    }

    public void process(List<String> caseNames) throws Exception {
        //BenchMarkProcessor将指定的用例集传递给BenchMarkRunner，
        //用例集可能是1个用例、也可能是N个用例，
        // 这取决于每个用例fork一个JVM、还是说连续N个用例使用一个JVM、还是说所有用例使用一个JVM
        forkOne(caseNames);
    }

    //所有用例fork一个jvm
    public void forkOne(List<String> caseNames) throws Exception {
        BenchMarkRunner benchMarkRunner = new BenchMarkRunner(runBenchmarkPath, jobId);
        benchMarkRunner.run(caseNames);
    }

    private String getRunBenchmark(String category, String systemName, Path workPath) {
        String runBenchmark;
        if (systemName.equals("Polars") && category.equals("JSY")) {
            workPath = workPath.resolve("bin").resolve("polars");
            runBenchmark = workPath.toString() + "/";
            runBenchmark += "run_jsy.sh";
        } else if (systemName.equals("Polars") && category.equals("BI")) {
            workPath = workPath.resolve("bin").resolve("polars");
            runBenchmark = workPath.toString() + "/";
            runBenchmark += "run_bi.sh";
        } else if (systemName.equals("Polars_MPP") && category.equals("JSY")) {
            workPath = workPath.resolve("bin").resolve("polars");
            runBenchmark = workPath.toString() + "/";
            runBenchmark += "run_jsy_mpp.sh";
        } else if (systemName.equals("Polars_MPP") && category.equals("BI")) {
            workPath = workPath.resolve("bin").resolve("polars");
            runBenchmark = workPath.toString() + "/";
            runBenchmark += "run_bi_mpp.sh";
        } else if (systemName.equals("SR")) {
            workPath = workPath.resolve("bin").resolve("sr");
            runBenchmark = workPath.toString() + "/";
            runBenchmark += "run_sr.sh";
        } else if (systemName.equals("SR_CS")) {
            workPath = workPath.resolve("bin").resolve("sr");
            runBenchmark = workPath.toString() + "/";
            runBenchmark += "run_sr_cs.sh";
        } else {
            throw new IllegalArgumentException("Unsupported category: " + systemName);
        }

        return runBenchmark;
    }

}