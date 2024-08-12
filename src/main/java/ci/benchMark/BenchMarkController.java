package ci.benchMark;

import base.cmd.ShellTool;
import base.db.JSYDBUtils;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Queue;
import java.util.Set;

/**
 * @author sunmuchao
 * @date 2023/11/15 3:43 下午
 */

public class BenchMarkController {
    private static FileLock lock;
    private static FileChannel channel;

    public static void main(String[] args) throws Exception {
        // 添加文件锁防止进程重复启动
        if (!acquireLock()) {
            System.out.println("Another instance is already running. Exiting.");
            System.exit(1);
        }

        try {
            String mode = System.getProperty("mode");
            if(mode.equals("import")){
                //如果是执行导入
                Import();
            }else if (mode.equals("run")){
                //如果执行的是发请求
                Run();
            }
        } finally {
            // 确保在应用程序退出时释放文件锁
            releaseLock();
        }
    }

    private static void Import() throws Exception {
        //工程执行路径
        Path workPath = Paths.get(System.getProperty("workPath"));
        //测试系统: Polars、SR、SR_CS、Polars_MPP
        String systemName = System.getProperty("systemName");
        String dataSource = System.getProperty("dataSource");
        BenchMarkImportProcessor benchMarkImportProcessor = new BenchMarkImportProcessor(workPath, systemName);
        benchMarkImportProcessor.process(dataSource);
    }

    public static void Run() {
        try {
            //工程执行路径
            Path workPath = Paths.get(System.getProperty("workPath"));
            //用例集,取自toml中的所有category
            String caseSet = System.getProperty("caseSet");
            String category;
            String dataSet = null;
            if (caseSet.contains(".")) {
                String[] cs = caseSet.split("\\.");
                category = cs[0];
                dataSet = cs[1];
            } else {
                category = caseSet;
            }

            //执行用例，用于调试单条用例或多条用例
            String caseNames = System.getProperty("caseNames");

            //剔除的用例
            String excludeCaseNames = System.getProperty("excludeCaseNames");

            //测试系统: Polars、SR、SR_CS、Polars_MPP
            List<String> systemNames = Arrays.asList(System.getProperty("systemNames").split(","));
            //是否更新到仪表板中
            Boolean isUpdateDashboard = Boolean.valueOf(System.getProperty("isUpdateDashboard"));

            String jobId = System.getProperty("jobId");

            List<String> allCaseNames = null;
            //需传递给benchMarkProcessor执行的用例集合
            if (!caseNames.trim().equals("")) {
                allCaseNames = Arrays.asList(caseNames.split(","));
                //获取toml文件中的category，并将category绑定到caseName上
                Path pbdsPath = workPath.resolve("benchmark").resolve("pbd");
                for(String caseName : allCaseNames){
                    File pbdFile = new File(String.valueOf(pbdsPath.resolve(caseName) + ".toml"));
                    PolarsBenchmarkDescription pbd = PolarsBenchmarkDescription.readFromFile(pbdFile.toString());
                    String category_tmp = pbd.getCategory();
                    if(category == null || category.equals(""))
                        category = category_tmp;
                    else if(!category.equals(category_tmp)){
                        System.out.println("不支持同时执行不同category集合，请检查用例");
                        return;
                    }
                }

            } else {
                allCaseNames = getAllCaseNames(category, dataSet, workPath);
            }

            allCaseNames = RemoveNotIncludedCases(allCaseNames, excludeCaseNames);

            for (String systemName : systemNames) {
                BenchMarkProcessor benchMarkProcessor = new BenchMarkProcessor(category, systemName, workPath, jobId);
                benchMarkProcessor.process(allCaseNames);
                if (isUpdateDashboard) {
                    //将结果写入到数据库中
                    ResultToDB(workPath, systemName);
                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static List<String> RemoveNotIncludedCases(List<String> allCaseNames, String excludeCaseNames1) {
        List<String> excludeCaseNames = Arrays.asList(excludeCaseNames1.split(","));
        allCaseNames.removeAll(excludeCaseNames);
        return allCaseNames;
    }


    public static void process1() {
        try {
            //String prid = System.getProperty("prid");
            //执行分支
            //String branch = System.getProperty("branch");
            //String codeType = System.getProperty("codeType");
            //工程执行路径
            Path workPath = Paths.get(System.getProperty("workPath"));
            //分类，例如：jsy、bi、sr
            //获取toml中的所有category来决定是否被调度
            String category = System.getProperty("category");

            //PR pr = new PR(branch, prid).setCodeType(codeType);

            //String runBenchmarkPath = getRunBenchmark(category, workPath);

            //BitBucketUtils bitBucketUtils = new BitBucketUtils();
            //拿到的所有历史PR均是数据库中存在结果的
            //Queue<PR> prQueue = bitBucketUtils.getResultPRQueue(branch, 3, codeType);

            //需传递给benchMarkProcessor执行的用例集合
            //List<String> allCaseNames = getAllCaseNames(category, workPath);

            //BenchMarkProcessor benchMarkProcessor = new BenchMarkProcessor(runBenchmarkPath, "polars");
            //benchMarkProcessor.process(allCaseNames);

            //将Polars的结果写入到数据库中
            ResultToDB(workPath, "polars");


            //processResults(workPath, pr, allCaseNames, prQueue);

            //重试逻辑
            //retry(benchMarkProcessor, pr, workPath, prQueue);

            //竞品执行，例如有新增用例则执行sr和其他竞品相关用例
            //competitorsExecute(workPath);

            //竞品执行
            /*runBenchmarkPath = getRunBenchmark("SR", workPath);
            benchMarkProcessor = new BenchMarkProcessor(runBenchmarkPath, "sr");
            benchMarkProcessor.process(allCaseNames);
*/
            //将SR的结果写入到数据库中
            ResultToDB(workPath, "sr");

            //结果处理器
            //BenchmarkResultDemonstrator brd = new BenchmarkResultDemonstrator(workPath);
            //brd.process();

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void competitorsExecute(Path workPath) throws Exception {
        //如果有新增用例，则需要执行竞品的相应用例
        //获取执行脚本路径

        //BenchMarkProcessor benchMarkProcessor = new BenchMarkProcessor("", "starrocks");
        Set<BenchmarkResultComponent2> allNewAddedCases = BenchmarkResultSet.getAllNewAddedCase();
        List<String> newAddedCaseNames = new ArrayList<>();
        for (BenchmarkResultComponent2 brc2 : allNewAddedCases) {
            newAddedCaseNames.add(brc2.getCaseName());
        }

        //benchMarkProcessor.process(newAddedCaseNames);
    }


    private static void processResults(Path workPath, PR pr, List<String> allCaseNames, Queue<PR> prQueue) throws Exception {
        //将结果写入到数据库中
        //ResultToDB(workPath, pr);

        //用于填充传给比较处理器的用例集
        List<String> caseset = setCaseSet(allCaseNames);

        //表单:用于填充比较集合的
        BenchmarkForm bf = new BenchmarkForm().setPrQueue(prQueue).setCurPr(pr);

        //第一个字段表单就是比较集合，例如：java、c++，polars、sr，pr1、pr2、pr3等
        //第一个字段传递的就是表单的查找方式，例如：根据pr1、pr2查找相应pr的结果数据，例如根据polars的对应prid和sr对应的版本id查找对应的结果数据
        //第二个字段就是用例名集合
        //调用比较处理器
        BenchmarkCompareProcessor bcp = new BenchmarkCompareProcessor(bf, caseset);
        bcp.process();
    }

    private static void retry(BenchMarkProcessor benchMarkProcessor, PR pr, Path workPath, Queue<PR> prQueue) throws Exception {
        //所有性能下降的都会重试三遍
        for (int i = 0; i < 3; i++) {
            Set<BenchmarkResultComponent2> allPerformanceReduceCase = BenchmarkResultSet.getAllPerformanceReduceCase();
            List<String> performanceReduceCaseNames = new ArrayList<>();
            if (allPerformanceReduceCase.size() > 0) {
                for (BenchmarkResultComponent2 brc2 : allPerformanceReduceCase) {
                    performanceReduceCaseNames.add(brc2.getCaseName());
                }

                benchMarkProcessor.process(performanceReduceCaseNames);

                processResults(workPath, pr, performanceReduceCaseNames, prQueue);

            } else {
                break;
            }
        }
    }

    private static List<String> setCaseSet(List<String> allCaseNames) {
        List<String> caseset = new ArrayList<>();
        caseset.addAll(allCaseNames);
        return caseset;
    }

    public static void ResultToDB(Path workPath, String systemName) throws Exception {
        File rsetDir = new File(workPath.resolve("rset").toString());
        String uuid = String.valueOf(System.currentTimeMillis());
        File[] files = rsetDir.listFiles();
        if (files != null) {
            for (File csv : files) {
                //以下操作要满足原子性
                if (csv.getName().toLowerCase().contains("_" + systemName.toLowerCase())) {
                    try {
                        JSYDBUtils.beginTx();
                        //String uuid = benchmarkResultMetaDataToDB(pr.getCodeType(), pr.getPrId());
                        csvResultToDB(csv, uuid, systemName);
                        JSYDBUtils.commit();
                    } catch (SQLException e) {
                        if (JSYDBUtils.getConnection() != null) {
                            JSYDBUtils.rollback();
                        }
                    } finally {
                        JSYDBUtils.close();
                    }
                }
            }
        } else {
            throw new Exception("results is null");
        }
    }

    private static String benchmarkResultMetaDataToDB(String codeType, String prid) {
        String uuid = String.valueOf(System.currentTimeMillis());

        String sql = "INSERT INTO benchmarkResultMetaData (codeType, prid, uuid) VALUES (\"" + codeType + "\", \"" + prid + "\", \"" + uuid + "\")";
        JSYDBUtils.updateData(sql);
        return uuid;
    }

    private static void csvResultToDB(File csv, String uuid, String systemName) throws IOException, SQLException {
        String tableName = null;
        if (systemName.equals("Polars")) {
            tableName = "benchmarkResult";
        } else if (systemName.equals("SR")) {
            tableName = "benchmarkSrResult";
        }

        try (Reader reader = new InputStreamReader(new FileInputStream(csv), StandardCharsets.UTF_8);
             CSVParser csvParser = new CSVParser(reader, CSVFormat.DEFAULT.withFirstRecordAsHeader().withQuote('"').withEscape('\\'))) {

            // Prepare the insert statement dynamically based on CSV headers
            String prefix = "INSERT INTO " + tableName + " (uuid,";
            StringBuilder insertQuery = new StringBuilder(prefix);
            StringBuilder valuePlaceholders = new StringBuilder(") VALUES (?,");

            // Get headers from CSV
            List<String> headers = csvParser.getHeaderNames();

            // Append column names and placeholders for values
            for (int i = 0; i < headers.size(); i++) {
                if (i > 0) {
                    insertQuery.append(", ");
                    valuePlaceholders.append(", ");
                }
                insertQuery.append(headers.get(i));
                valuePlaceholders.append("?");
            }

            insertQuery.append(valuePlaceholders).append(")");
            System.out.println("insertQuery:" + insertQuery.toString());
            PreparedStatement preparedStatement = JSYDBUtils.getConnection().prepareStatement(insertQuery.toString());

            for (CSVRecord record : csvParser) {
                preparedStatement.setString(1, uuid);
                for (int i = 0; i < headers.size(); i++) {
                    String columnName = headers.get(i);
                    String value = record.get(columnName);

                    preparedStatement.setString(i + 2, value);
                }

                preparedStatement.executeUpdate();
            }
        }
    }

    /*private static void csvResultToDB(File csv, String uuid) throws IOException, SQLException {
        try (Reader reader = new InputStreamReader(new FileInputStream(csv), StandardCharsets.UTF_8);
             CSVParser csvParser = new CSVParser(reader, CSVFormat.DEFAULT.withFirstRecordAsHeader().withQuote('"').withEscape('\\'))) {

            // Prepare the insert statement dynamically based on CSV headers
            StringBuilder insertQuery = new StringBuilder("INSERT INTO benchmarkResult (uuid,");
            StringBuilder valuePlaceholders = new StringBuilder(") VALUES (?,");

            // Get headers from CSV
            List<String> headers = csvParser.getHeaderNames();

            // Append column names and placeholders for values
            for (int i = 0; i < headers.size(); i++) {
                if (i > 0) {
                    insertQuery.append(", ");
                    valuePlaceholders.append(", ");
                }
                insertQuery.append(headers.get(i));
                valuePlaceholders.append("?");
            }

            insertQuery.append(valuePlaceholders).append(")");
            System.out.println("insertQuery:" + insertQuery.toString());
            PreparedStatement preparedStatement = JSYDBUtils.getConnection().prepareStatement(insertQuery.toString());

            for (CSVRecord record : csvParser) {
                preparedStatement.setString(1, uuid);
                for (int i = 0; i < headers.size(); i++) {
                    String columnName = headers.get(i);
                    String value = record.get(columnName);

                    preparedStatement.setString(i + 2, value);
                }

                preparedStatement.executeUpdate();
            }
        }
    }*/

    private static void deleteDuplicate(PR pr, CSVRecord record) throws Exception {
        //判断数据库中是否包含，如果包含就进行删除
        String querySql = "select count(*) as count from benchmarkResult where codeType=\"" + pr.getCodeType() + "\" and prid=" + Integer.parseInt(pr.getPrId()) + " and id=\"" + record.get("id") + "\"";
        List<Map<String, String>> result = JSYDBUtils.query(querySql, "count");
        if (Integer.parseInt(result.get(0).get("count")) > 0) {
            String deleteSql = "delete from benchmarkResult where codeType=\"" + pr.getCodeType() + "\" and prid=" + Integer.parseInt(pr.getPrId()) + " and id=\"" + record.get("id") + "\"";
            JSYDBUtils.updateData(deleteSql);
        }
    }

    private static String getSrRunBenchmark(Path workPath) {
        workPath = workPath.resolve("bin");
        String runBenchmark = workPath.toString() + "/";
        //完成一个脚本执行sr的用例


        return runBenchmark;
    }

    private static List<String> getAllCaseNames(String category, String dataSet, Path workPath) throws IOException {
        List<String> caseNames = new ArrayList();
        Path pbdsPath = workPath.resolve("benchmark").resolve("pbd");
        Path plsPath = workPath.resolve("pls");
        //遍历所有用例名，然后通过-Dpbds参数进行填充，这里用来之后的的调度相关的扩展
        File pbds = new File(String.valueOf(pbdsPath));

        File[] files = pbds.listFiles();
        if (files != null) {
            for (File file : files) {
                if (!file.getName().equals("") && file.getName().endsWith(".toml")) {
                    PolarsBenchmarkDescription pbd = PolarsBenchmarkDescription.readFromFile(file.toString());

                    //检测文件是否合规
                    File plsFile = new File(String.valueOf(plsPath.resolve(pbd.getPls())));
                    //File srFile = new File(String.valueOf(plsPath.resolve(pbd.sqls())));
                    if (!plsFile.exists()) {
                        System.out.println(file.getName() + "中的 pls:" + plsFile + "不存在");
                        //System.exit(0);
                        continue;
                    }

                    /*if (!srFile.exists()) {
                        System.out.println(file.getName() + "中的 sr的sql:" + srFile + "不存在");
                        //System.exit(0);
                        continue;
                    }*/

                    if (pbd.getCategory().equals(category)) {
                        if (dataSet != null && pbd.getDataSet().equals(dataSet)) {
                            caseNames.add(file.getName().split("\\.")[0]);
                        } else if (dataSet == null){
                            caseNames.add(file.getName().split("\\.")[0]);
                        }
                    }
                }
            }
        }
        if(caseNames.size() == 0) {
            throw new IllegalArgumentException("The number of executed use cases is 0");
        }
        return caseNames;
    }


    private static boolean acquireLock() {
        try {
            File lockFile = new File("app.lock");
            channel = new FileOutputStream(lockFile).getChannel();
            lock = channel.tryLock();
            return lock != null;
        } catch (IOException e) {
            throw new RuntimeException("Could not create or lock the file", e);
        }
    }

    private static void releaseLock() {
        try {
            if (lock != null) {
                lock.release();
                channel.close();
                new File("app.lock").delete();
            }
        } catch (IOException e) {
            throw new RuntimeException("Could not release or delete the lock file", e);
        }
    }

}
