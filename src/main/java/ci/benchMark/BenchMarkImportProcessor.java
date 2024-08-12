package ci.benchMark;

import base.cmd.ShellTool;

import java.nio.file.Path;
import java.util.List;

/**
 * @author sunmuchao
 * @date 2024/7/31 2:57 下午
 */
public class BenchMarkImportProcessor {
    private String systemName;
    private String runBenchmarkPath;
    public BenchMarkImportProcessor(Path workPath, String systemName) {
        this.systemName = systemName;
        this.runBenchmarkPath = getRunBenchmark(systemName, workPath);
    }

    private String getRunBenchmark(String systemName, Path workPath){
        String runBenchmark;
        if (systemName.equals("Polars")) {
            workPath = workPath.resolve("bin").resolve("polars");
            runBenchmark = workPath.toString() + "/";
            runBenchmark += "prepare_bi_mpp.sh";
        } else if (systemName.equals("SR")) {
            workPath = workPath.resolve("bin").resolve("sr");
            runBenchmark = workPath.toString() + "/";
            runBenchmark += "import_sr.sh";
        } else if (systemName.equals("SR_CS")) {
            workPath = workPath.resolve("bin").resolve("sr");
            runBenchmark = workPath.toString() + "/";
            runBenchmark += "import_sr_cs.sh";
        } else {
            throw new IllegalArgumentException("Unsupported category: " + systemName);
        }

        return runBenchmark;
    }

    public void process(String dataSource) throws Exception {
        ShellTool.cmd("sh " + runBenchmarkPath + " " + dataSource);
    }
}
