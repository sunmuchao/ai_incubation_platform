package ci.benchMark.comparator;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.io.Reader;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import com.moandjiezana.toml.Toml;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;

/**
 * @author sunmuchao
 * @date 2024/7/18 3:26 下午
 */
public class SRQueryPbdBenchMarkRunner {
    private static String errorInfo;

    public static void main(String[] args) {
        String jobId = System.getProperty("jobId");
        String pbds = System.getProperty("pbds");
        String conf = System.getProperty("conf");
        int measureCount = 3; // 每个SQL查询的尝试次数
        int warmCount = 1; //预热次数
        String engine;

        try {
            // 确定项目目录
            Path projectDir = Paths.get(args[0]);
            String binPath = Paths.get(projectDir.toString(), "bin").toString();
            String rsetPath = Paths.get(projectDir.toString(), "rset").toString();
            String confFile = Paths.get(binPath, "..", "conf", conf).toString();
            File pbdDir = new File(projectDir.resolve("benchmark").resolve("pbd").toString());

            // 初始化变量
            List<String> removeArray = new ArrayList<>();

            // 从starrocks_separation.conf文件中读取数据库连接详细信息
            String fe_ip = getConfValue(confFile, "mysql_host");
            String fe_port = getConfValue(confFile, "mysql_port");
            String database = getConfValue(confFile, "database");

            Boolean isClean = Boolean.valueOf(System.getProperty("clean"));
            if (isClean) {
                File rsetDir = new File(rsetPath);
                if (rsetDir.exists() && rsetDir.isDirectory()) {
                    clearDirectory(rsetDir);
                    System.out.println("rset directory cleaned.");
                } else {
                    System.out.println("rset directory does not exist or is not a directory.");
                }
            }
            ArrayList<String> pbdList = null;
            List<File> pbdFiles = new ArrayList<>();
            if (pbds != null && !pbds.isEmpty()) {
                pbds = pbds.substring(0, pbds.length());
                pbdList = new ArrayList<>(Arrays.asList(pbds.split(",")));

                Path bakPath = projectDir.resolve("rset").resolve("bak");
                try (DirectoryStream<Path> stream = Files.newDirectoryStream(bakPath, "*" + jobId + "-sr.csv")) {
                    for (Path csvFilePath : stream) {
                        removeArray.addAll(readPbdNameColumnFromCsv(csvFilePath.toFile()));
                    }
                } catch (IOException e) {
                    System.err.println("Error processing CSV files: " + e.getMessage());
                }
                pbdList.removeAll(removeArray);

                if (pbdList.size() == 0) {
                    System.out.println("需执行用例数为0");
                    return;
                }

                for (String pbd : pbdList) {
                    String pbdfileName = pbd.trim() + ".toml";
                    File pbdFile = new File(pbdDir, pbdfileName);
                    if (pbdFile.exists()) {
                        pbdFiles.add(pbdFile);
                    } else {
                        System.err.println("File not found: " + pbdfileName);
                    }
                }
            } else {
                pbdFiles = Arrays.asList(pbdDir.listFiles((dir, name) -> name.endsWith(".toml")));
            }

            engine = getEngineType(fe_ip, fe_port, database);


            // 为每个QUERY_NAME执行查询
            for (File pbdFile : pbdFiles) {
                String TOML_FILE = pbdFile.toString();
                String SQL_FILE = getTomlValue(TOML_FILE, "sqls.starrocks").replaceAll("\"", "");
                String QUERY_ID = getTomlValue(TOML_FILE, "id").replaceAll("\"", "");
                String SQL_PATH = Paths.get(binPath, "..", "competitors", "starrocks", "query", SQL_FILE).toString();

                System.out.println("SQL_PATH: " + SQL_PATH);

                String RESULT_FILE = Paths.get(binPath, "..", "rset", jobId + "_" + QUERY_ID + "_sr.csv").toString();
                File resultFile = new File(RESULT_FILE);
                resultFile.getParentFile().mkdirs();
                resultFile.createNewFile();

                try (FileWriter writer = new FileWriter(resultFile)) {
                    writer.write("id,pbdName,engine,warmCount,warmTime,measureCount,measureTime,starttime,errorInfo\n");

                    if (new File(SQL_PATH).exists()) {
                        System.out.println("文件存在。");
                    } else {
                        System.out.println("文件不存在。");
                    }

                    if (Files.size(Paths.get(SQL_PATH)) > 0) {
                        System.out.println("文件不为空。");
                    } else {
                        System.out.println("文件为空。");
                    }

                    String pbdName = pbdFile.getName().split("\\.")[0];
                    List<String> queries = Files.readAllLines(Paths.get(SQL_PATH));
                    for (String query : queries) {
                        System.out.println("执行查询: " + query);
                        writer.write(QUERY_ID + "," + pbdName + ",");

                        int warmTime = 0;
                        int measureTime = 0;

                        //先预热
                        for (int i = 1; i <= warmCount; i++) {
                            long time = executeMySQLQuery(fe_ip, fe_port, database, query);
                            warmTime += time;
                        }

                        for (int i = 1; i <= measureCount; i++) {
                            long time = executeMySQLQuery(fe_ip, fe_port, database, query);
                            measureTime += time;
                        }

                        if (errorInfo != null) measureTime = 0;
                        long currentTimestamp = System.currentTimeMillis() / 1000L;
                        //engine,warmCount,warmTime,measureCount,measureTime,starttime,errorInfo
                        writer.write(engine + "," + warmCount + "," + warmTime + "," + measureCount + "," + measureTime + "," + currentTimestamp + ",\"" + errorInfo + "\"\n");
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static String getConfValue(String confFile, String key) throws IOException {
        try (BufferedReader br = new BufferedReader(new FileReader(confFile))) {
            String line;
            while ((line = br.readLine()) != null) {
                if (line.startsWith(key)) {
                    return line.split("\\s+")[1];
                }
            }
        }
        throw new IOException("在conf文件中未找到键: " + key);
    }

    private static String getTomlValue(String tomlFile, String key) throws IOException {
        Toml toml = new Toml().read(new File(tomlFile));
        return toml.getString(key);
    }

    public static long executeMySQLQuery(String fe_ip, String fe_port, String database, String query) {
        long startTime = System.currentTimeMillis();
        String url = "jdbc:mysql://" + fe_ip + ":" + fe_port + "/" + database;
        List<Map<String, Object>> results = new ArrayList<>();

        try (Connection conn = DriverManager.getConnection(url, "root", "");
             Statement stmt = conn.createStatement()) {

            if (query.trim().toLowerCase().startsWith("select")) {
                try (ResultSet rs = stmt.executeQuery(query)) {
                    ResultSetMetaData metaData = rs.getMetaData();
                    int columnCount = metaData.getColumnCount();

                    while (rs.next()) {
                        Map<String, Object> row = new HashMap<>();
                        for (int i = 1; i <= columnCount; i++) {
                            row.put(metaData.getColumnName(i), rs.getObject(i));
                        }
                        results.add(row);
                    }
                }
            } else {
                stmt.execute(query);
            }
        } catch (Exception e) {
            errorInfo = e.getMessage();
            e.printStackTrace();
        }

        long endTime = System.currentTimeMillis();
        return endTime - startTime;
    }

    public static String getEngineType(String fe_ip, String fe_port, String database) {
        String query = "SHOW BACKENDS;";
        String url = "jdbc:mysql://" + fe_ip + ":" + fe_port + "/" + database;

        try (Connection conn = DriverManager.getConnection(url, "root", "");
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(query)) {

            if (!rs.next()) {
                // If the result set is empty, it's a storage-compute separated engine
                return "separated";
            }
        } catch (Exception e) {
            errorInfo = e.getMessage();
            e.printStackTrace();
        }

        // If the result set is not empty, it's an integrated storage-compute engine
        return "integrated";
    }

    private static void clearDirectory(File directory) {
        File[] files = directory.listFiles();
        if (files != null) {
            for (File file : files) {
                if (!file.isDirectory()) {
                    file.delete();
                }
            }
        }
    }

    private static List<String> readPbdNameColumnFromCsv(File csvFile) {
        List<String> plsData = new ArrayList<>();
        try (Reader reader = new FileReader(csvFile);
             CSVParser csvParser = new CSVParser(reader, CSVFormat.DEFAULT.withFirstRecordAsHeader())) {

            for (CSVRecord record : csvParser) {
                String sqlNameValue = record.get("pbdName");
                String plsPrefix = sqlNameValue.split("\\.")[0];
                plsData.add(plsPrefix);
            }
        } catch (IOException e) {
            System.err.println("Error reading CSV file: " + e.getMessage());
        }
        return plsData;
    }
}
