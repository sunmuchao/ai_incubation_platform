package profile;

import com.opencsv.CSVParser;
import com.opencsv.CSVParserBuilder;
import com.opencsv.CSVReader;
import com.opencsv.CSVReaderBuilder;
import com.opencsv.enums.CSVReaderNullFieldIndicator;

import java.io.BufferedReader;
import java.io.FileNotFoundException;
import java.io.FileReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * @author sunmuchao
 * @date 2023/7/31 4:11 下午
 */
public class ScheduledExportProfile {
    public static void main(String[] args) {
        ScheduledExecutorService executorService = Executors.newSingleThreadScheduledExecutor();

        // 执行定时任务
        executorService.scheduleAtFixedRate(() -> {
            // 获取昨天和今天的时间
            Calendar calendar = Calendar.getInstance();
            calendar.add(Calendar.DAY_OF_MONTH, -1);
            Date yesterday = calendar.getTime();
            Date today = new Date();
            SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");




            String csvFilePath = args[0];
            String jdbcUrl = "jdbc:postgresql://124.70.154.253:5432/sun";
            String username = "sun";
            String password = "WLSFKMmt66";
            String tableName = "TerminateTaskInfoTable";
            String homePath = args[1];

            try {
                System.out.println(yesterday);
                System.out.println(today);
                executeTask(homePath, csvFilePath, jdbcUrl, username, password, tableName, sdf.format(yesterday), sdf.format(today));
            } catch (IOException | InterruptedException e) {
                e.printStackTrace();
            }
        }, 0, 1, TimeUnit.DAYS);

        // 等待定时任务执行完成后关闭executorService
        //executorService.shutdown();
    }

    public static void executeTask(String homePath, String csvFilePath, String jdbcUrl, String username, String password,
                                   String tableName, String startTime, String endTime) throws IOException, InterruptedException {

        // 定义Shell命令
        String[] command = {
                "java",
                "-cp",
                "/data/smc/polars-analysePersistTask/polars-assembly-1.0-SNAPSHOT.jar",
                "com.fanruan.polars.shell.AnalysePersistTaskProfiler",
                homePath,
                String.valueOf(startTime),
                String.valueOf(endTime),
                csvFilePath,
                "select * from TerminateTaskInfoTable where create_time >= '" + String.valueOf(startTime) + "' and create_time <= '" + String.valueOf(endTime) + "'"
        };

        // 创建进程并执行命令
        ProcessBuilder processBuilder = new ProcessBuilder(command);
        processBuilder.redirectErrorStream(true); // 将标准错误输出合并到标准输出
        Process process = processBuilder.start();

        // 读取进程的输出
        BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()));
        String line;
        while ((line = reader.readLine()) != null) {
            System.out.println(line);
        }

        // 等待命令执行完成
        int exitCode = process.waitFor();
        System.out.println("Command executed, exit code: " + exitCode);

        // 设置每一批次插入的数据量
        int batchSize = 1000;

        try (Connection connection = DriverManager.getConnection(jdbcUrl, username, password)) {
            // 读取CSV文件
            int count = 0;
            int total = 0;
            StringBuilder sqlBuilder = new StringBuilder();

            // 构建SQL插入语句
            sqlBuilder.append("INSERT INTO ").append(tableName).append("(name, status, type, create_time, end_time, queue_time, wait_resource_time, ")
                    .append("plan_time, start_time, run_time, finish_time, execution_all_time, mem_peak, mem_current, mem_capacity, pool_name, ")
                    .append("work_node, task_desc, cancel_message, failed_message, failed_exception, error_messages) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");

            try (PreparedStatement preparedStatement = connection.prepareStatement(sqlBuilder.toString())) {
                CSVParser csvParser = new CSVParserBuilder()
                        .withSeparator(',')
                        .withQuoteChar('"')
                        .withEscapeChar('\\')
                        .withFieldAsNull(CSVReaderNullFieldIndicator.EMPTY_QUOTES)
                        .build();

                CSVReader csvReader = new CSVReaderBuilder(new FileReader(csvFilePath))
                        .withCSVParser(csvParser)
                        .build();

                String[] nextRecord;
                while ((nextRecord = csvReader.readNext()) != null) {
                    if (nextRecord[0] != null) {
                        // 处理CSV文件的每一行数据
                        // 添加数据到批处理中
                        addDataToBatch(preparedStatement, nextRecord);
                        count++;
                        // 达到批次大小时执行批量插入
                        if (count == batchSize) {
                            count = 0;
                            total += batchSize;
                            preparedStatement.executeBatch();
                        }
                    }
                }

                // 执行剩余的数据
                if (count > 0) {
                    total += count;
                    preparedStatement.executeBatch();
                }

                System.out.println("Total records inserted: " + total);
            } catch (ParseException | SQLException | FileNotFoundException e) {
                e.printStackTrace();
            } catch (IOException e) {
                e.printStackTrace();
            }
        } catch (SQLException throwables) {
            throwables.printStackTrace();
        }

    }

    private static void addDataToBatch(PreparedStatement preparedStatement, String[] fields) throws SQLException, ParseException {
        SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        for (int i = 0; i < fields.length; i++) {
            switch (i) {
                case 0: // name
                case 1: // status
                case 2: // type
                case 15: // mem_capacity
                case 16: // pool_name
                case 17: // work_node
                case 18: // task_desc
                case 19: // cancel_message
                case 20: // failed_message
                case 21: // failed_exception
                case 22: // error_messages
                    preparedStatement.setString(i + 1, fields[i]);
                    break;
                case 3: // create_time
                case 4: // end_time
                    Date date = sdf.parse(fields[i]);
                    preparedStatement.setTimestamp(i + 1, new java.sql.Timestamp(date.getTime()));
                    break;
                default: // bigint类型字段
                    long value = Long.parseLong(fields[i]);
                    preparedStatement.setLong(i + 1, value);
                    break;
            }
        }
        preparedStatement.addBatch();
    }
}
