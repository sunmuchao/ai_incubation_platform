package buriedPoint;

import buriedPoint.executor.DataFlowExecutor;
import buriedPoint.executor.QueryExecutor;
import buriedPoint.point.BuriedPoint;
import metric.MetricParser;

import java.io.*;
import java.net.URL;
import java.net.URLConnection;
import java.sql.*;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import base.config.Application;
import base.third.jira.JiraUtils;

public class BugPusher {
    private String cookie;
    private BuriedPoint buriedPoint;
    private String traceid;
    private DBUtils dbUtils;
    private String description;
    public boolean interrupt = false;

    private JiraUtils jiraUtils;

    public BugPusher(String cookie, BuriedPoint buriedPoint, String traceid, DBUtils dbUtils) {
        this.buriedPoint = buriedPoint;
        this.cookie = cookie;
        this.traceid = traceid;
        this.dbUtils = dbUtils;
        this.jiraUtils = new JiraUtils(dbUtils);
        description = "zipkin:https://work.jiushuyun.com/decision/zipkin/traces/" + traceid +
                "\npolars总耗时:" + buriedPoint.getTotoalPolarsTime();
        if(buriedPoint.getReasons().size() > 0) {
            description += "\n可能的原因：";
            for(String reason : buriedPoint.getReasons()){
                description += reason + "\n";
            }
        }
    }

    public void pushBug(String traceid, DBUtils dbUtils) throws IOException, SQLException {
        if(Application.jiraSwitch) {
            String trace = jiraUtils.createIssue(buriedPoint, traceid, description);
            if (buriedPoint.getReasons().size() > 0) {
                if (buriedPoint.getClass().getName().contains("UpdateBuriedPoint")) {
                    dbUtils.resIntoDBAndTraceJob(traceid, buriedPoint.getReasons(), 1, "jsyUpdate", trace);
                } else {
                    dbUtils.resIntoDBAndTraceJob(traceid, buriedPoint.getReasons(), 1, "jsy", trace);
                }
            }
            //将bug的表名、用户名、耗时写入到数据库中
            BugToDB();
            System.out.println("推送bug");
        }
    }

    //返回true表示非bug或表已经被删除
    public Boolean addResult(QueryExecutor queryExecutor) throws Exception {
        File saveDir = new File(Application.workPath);
        System.out.println("Metric=" + queryExecutor.getMetric());
        downfile(queryExecutor.getMetric(), saveDir, traceid, "metric/");
        Application.setSuitePath(queryExecutor.getSuite());
        //提供metric解析器
        MetricParser merMetricParser = new MetricParser( saveDir + "/" + traceid + ".metric");
        merMetricParser.parse();

        File metricFile = new File(saveDir + "/" + traceid + ".metric");
        String lastLine = readLastLine(metricFile);
        if (lastLine.contains("OutputOperator")) {
            //查看metric所在的行
            BufferedReader reader = new BufferedReader(new FileReader(metricFile));
            String line = null;
            int MaxRows = 0;
            queryExecutor.setOpenTime(Integer.parseInt(lastLine.split("sum=")[1].split("ms")[0]));
            queryExecutor.setRealPolarsTime(Integer.parseInt(lastLine.split("sum=")[1].split("ms")[0]) + Integer.parseInt(lastLine.split("sum=")[2].split("ms")[0]));
            boolean open = false;
            while ((line = reader.readLine()) != null && !line.equals(lastLine)) {
                if (line.trim().equals("metric:")) {
                    open = true;
                    continue;
                }
                if (open) {
                    int rows = Integer.parseInt(line.split("rows=")[1].split(" ")[0]);
                    MaxRows = (MaxRows > rows) ? MaxRows : rows;
                }
            }
            queryExecutor.setMaxRows(MaxRows);

            if (queryExecutor.getMaxRows() > 100000 && queryExecutor.getRealPolarsTime() < 3000) {
                dbUtils.resIntoDB(traceid, "10w行以上，3s以下属于合理耗时", 0, "jsy");
                return true;
            }


            if (queryExecutor.getMaxRows() > 1000000) {
                if (queryExecutor.getStepNumber() >= 25 && queryExecutor.getRealPolarsTime() <= 5000) {
                    dbUtils.resIntoDB(traceid, "百万级别的,25个步骤,5s以下属于合理耗时", 0, "jsy");
                    return true;
                } else if (queryExecutor.getStepNumber() >= 35 && queryExecutor.getRealPolarsTime() <= 7000) {
                    dbUtils.resIntoDB(traceid, "百万级别的,35个步骤,7s以下属于合理耗时", 0, "jsy");
                    return true;
                }

            }

            if (queryExecutor.getClos() >= 100 && queryExecutor.getOpenTime() > 1000000) {
                dbUtils.resIntoDB(traceid, "列过多导致的open慢", 0, "jsy");
                return true;
            }

            if ((queryExecutor.getRealPolarsTime() - queryExecutor.getOpenTime()) != 0 &&
                    (queryExecutor.getqueryExecutorTime() - queryExecutor.getRealPolarsTime() > queryExecutor.getqueryExecutorTime() * 0.5)) {
                dbUtils.resIntoDB(traceid, "引擎内部排队导致", 0, "jsy");
                return true;
            }
            queryExecutor.setClos(Integer.parseInt(lastLine.split("cols=")[1]));
            if (queryExecutor.getClos() >= 400) {
                dbUtils.resIntoDB(traceid, "列数过多", 0, "jsy");
                return true;
            }

            if (queryExecutor.getClos() >= 100 && queryExecutor.getClos() <= 200 && queryExecutor.getRealPolarsTime() < 3500) {
                dbUtils.resIntoDB(traceid, "列数过多", 0, "jsy");
                return true;
            }


            queryExecutor.setStepNumber(Integer.parseInt(lastLine.split(" ")[0]));
            if (queryExecutor.getStepNumber() >= 50) {
                dbUtils.resIntoDB(traceid, "步骤过多", 0, "jsy");
                return true;
            }

            if (queryExecutor.getStepNumber() >= 20 && queryExecutor.getStepNumber() <= 30
                    && queryExecutor.getRealPolarsTime() >= 1000 && queryExecutor.getRealPolarsTime() <= 2000) {
                dbUtils.resIntoDB(traceid, "步骤过多", 0, "jsy");
                return true;
            }

        } else if (lastLine.contains("No such file or directory")) {
            dbUtils.resIntoDB(traceid, "metric数据丢失", 0, "jsy");
            return true;

        } else if(lastLine.contains("metric:")){
            dbUtils.resIntoDB(traceid, "metric信息没打印", 0, "jsy");
            return true;
        }

        //suite加超时杀死机制，因为如果存在但是文件很大的话，就会下载很长时间
        Boolean isExistFile = interruptibleDownFile(queryExecutor.getSuite(), saveDir, traceid, "suite");
        System.out.println("小文件的suite=" + queryExecutor.getSuite());
        if (isExistFile) {
            File file = new File(saveDir + "/" + traceid + ".suite");
            BufferedReader reader = new BufferedReader(new FileReader(file));
            String line = reader.readLine();
            if (line.contains("can't find table")) {
                System.out.println("表已被删除");
                dbUtils.resIntoDB(traceid, "表已被删除", 0, "jsy");
                return true;
            }
        }
        //不需要下载suite文件
        /*} else if (line.contains("data file is to large")) {
            Thread thread = new Thread(new Runnable() {
                @Override
                public void run() {
                    try {
                        queryExecutor.setSuite("https://qfx30.oss-cn-hangzhou.aliyuncs.com/qfx3/WEB-INF/polars/suite/" + queryExecutor.getPls().split("/")[9].split("\\.")[0] + ".suite2");
                        downfile(queryExecutor.getSuite(), saveDir, traceid, "suite");
                        System.out.println("大文件的suite=" + queryExecutor.getSuite());
                    } catch (IOException e) {
                        e.printStackTrace();
                    }
                }
            });
            thread.start();
        }*/
        description += "\nmetric:  " + queryExecutor.getMetric() +
                "\npls:  " + queryExecutor.getPls() +
                "\nsuite:  " + queryExecutor.getSuite();

        //不需要下载pls
        //downfile(queryExecutor.getPls(), saveDir, traceid, "pls");
        //System.out.println(queryExecutor.getPls());
        return false;
    }

    public void BugToDB() throws SQLException {
        String tableName = null;
        System.out.println(buriedPoint.getUserName());
        System.out.println(buriedPoint.getTableName());
        System.out.println(buriedPoint.getWidgetName());
        //if (!buriedPoint.getUserName().isEmpty() && !(buriedPoint.getTableName().isEmpty() && buriedPoint.getWidgetName().isEmpty())) {
        if (buriedPoint.getTableName() != null) {
            tableName = buriedPoint.getTableName();
        } else if (buriedPoint.getWidgetName() != null) {
            tableName = buriedPoint.getWidgetName();
        }

        System.out.println("select table_name from BuriedPointUserMessage where user_name=\"" +
                buriedPoint.getUserName() + "\" and table_name=\"" + tableName + "\";");

        ResultSet rs = dbUtils.SelectData("select table_name from BuriedPointUserMessage where user_name=\"" +
                buriedPoint.getUserName() + "\" and table_name=\"" + tableName + "\";");
        if (!rs.next()) {
            if (buriedPoint.getClass().getName().contains("UpdateBuriedPoint")) {
                System.out.println("insert into BuriedPointUserMessage (user_name, table_name, updateTime) values " +
                        "(\"" + buriedPoint.getUserName() + "\",\"" + tableName + "\"," + buriedPoint.getTotalTime() + ");");
                dbUtils.updateData("insert into BuriedPointUserMessage (user_name, table_name, updateTime) values " +
                        "(\"" + buriedPoint.getUserName() + "\",\"" + tableName + "\"," + buriedPoint.getTotalTime() + ");");
            } else {
                System.out.println("insert into BuriedPointUserMessage (user_name, table_name, time) values " +
                        "(\"" + buriedPoint.getUserName() + "\",\"" + tableName + "\"," + buriedPoint.getTotalTime() + ");");
                dbUtils.updateData("insert into BuriedPointUserMessage (user_name, table_name, time) values " +
                        "(\"" + buriedPoint.getUserName() + "\",\"" + tableName + "\"," + buriedPoint.getTotalTime() + ");");
            }
        }
        //}
    }



    public boolean addUpdateResult(DataFlowExecutor executor) throws Exception {
        File saveDir = new File(Application.workPath);
        System.out.println("Metric=" + executor.getMetric());
        downfile(executor.getMetric(), saveDir, traceid, "metric/");
        Application.setSuitePath(executor.getSuite());
        //提供metric解析器
        MetricParser merMetricParser = new MetricParser( saveDir + "/" + traceid + ".metric");
        merMetricParser.parse();

        File metricFile = new File(saveDir + "/" + traceid + ".metric");
        BufferedReader reader = new BufferedReader(new FileReader(metricFile));

        String line = null;
        int MaxRows = 0;
        String lastLine = readLastLine(metricFile);
        if (lastLine.equals("")) {
            dbUtils.resIntoDB(traceid, "metric数据为空", 0, "jsyUpdate");
            System.out.println("由于metric数据为空导致的:interrupt=true");
            interrupt = true;
            return true;
        }
        executor.setStepNumber(Integer.parseInt(lastLine.split(" ")[0]));
        boolean open = false;

        while ((line = reader.readLine()) != null && !line.equals(lastLine)) {
            if (line.trim().equals("metric:")) {
                open = true;
                continue;
            }
            if (open) {
                int rows = Integer.parseInt(line.split("rows=")[1].split(" ")[0]);
                MaxRows = (MaxRows > rows) ? MaxRows : rows;
                if (line.contains("·OutputOperator ") || line.contains("?OutputOperator ") ) {
                    executor.setCalculationTime(Integer.parseInt(line.split("sum=")[1].split("ms")[0]) + Integer.parseInt(line.split("sum=")[2].split("ms")[0]));
                } else if (line.contains("ChecksumImportDataBracket")) {
                    executor.setOpenTime(Integer.parseInt(line.split("sum=")[1].split("ms")[0]));
                    executor.setRealPolarsTime(Integer.parseInt(line.split("sum=")[1].split("ms")[0]) + Integer.parseInt(line.split("sum=")[2].split("ms")[0]));
                    executor.setChecksumImportDataBracketTime(executor.getRealPolarsTime() - executor.getCalculationTime());
                }
            }
        }

        executor.setMaxRows(MaxRows);

        if (executor.getMaxRows() >= 10000000) {
            interrupt = true;
            System.out.println("由于上层父表数量级大于1kw导致的:interrupt=true");
            dbUtils.resIntoDB(traceid, "上层父表数量级大于1kw", 0, "jsyUpdate");
            return true;
        }

        if (executor.getMaxRows() > 100000 && executor.getRealPolarsTime() < 3000) {
            dbUtils.resIntoDB(traceid, "10w行以上，3s以下属于合理耗时", 0, "jsyUpdate");
            return true;
        }


        if (executor.getMaxRows() > 1000000) {
            if (executor.getStepNumber() >= 25 && executor.getRealPolarsTime() <= 5000) {
                dbUtils.resIntoDB(traceid, "百万级别的,25个步骤,5s以下属于合理耗时", 0, "jsyUpdate");
                return true;
            } else if (executor.getStepNumber() >= 35 && executor.getRealPolarsTime() <= 7000) {
                dbUtils.resIntoDB(traceid, "百万级别的,35个步骤,7s以下属于合理耗时", 0, "jsyUpdate");
                return true;
            }

        }

        if (executor.getClos() >= 100 && executor.getOpenTime() > 1000000) {
            dbUtils.resIntoDB(traceid,"列过多导致的open慢",0, "jsyUpdate");
            return true;
        }

        if(executor.getClos() < 100 && executor.getOpenTime() > 10000000){
            return jiraUtils.isnotNewProblem("open慢",buriedPoint);
        }

        if ((executor.getRealPolarsTime() - executor.getOpenTime()) != 0 &&
                (executor.getDataFlowExecutorTime() - executor.getRealPolarsTime() > executor.getDataFlowExecutorTime() * 0.5)) {
            dbUtils.resIntoDB(traceid, "引擎内部排队导致", 0, "jsyUpdate");
            return true;
        }
        executor.setClos(Integer.parseInt(lastLine.split("cols=")[1]));
        if (executor.getClos() >= 400) {
            dbUtils.resIntoDB(traceid, "列数过多", 0, "jsyUpdate");
            return true;
        }

        if (executor.getClos() >= 100 && executor.getClos() <= 200 && executor.getRealPolarsTime() < 3500) {
            dbUtils.resIntoDB(traceid, "列数过多", 0, "jsyUpdate");
            return true;
        }


        executor.setStepNumber(Integer.parseInt(lastLine.split(" ")[0]));
        if (executor.getStepNumber() >= 50) {
            dbUtils.resIntoDB(traceid, "步骤过多", 0, "jsyUpdate");
            return true;
        }

        if (executor.getStepNumber() >= 20 && executor.getStepNumber() <= 30
                && executor.getRealPolarsTime() >= 1000 && executor.getRealPolarsTime() <= 2000) {
            dbUtils.resIntoDB(traceid, "步骤过多", 0, "jsyUpdate");
            return true;
        }

        return false;
    }

    public static String readLastLine(File file) {
        String lastLine = "";
        try (BufferedReader bufferedReader = new BufferedReader(new FileReader(file))) {
            String currentLine = "";
            while (!(currentLine = bufferedReader.readLine()).equals("") || !(bufferedReader.readLine()).equals("")) {
                lastLine = currentLine;
            }
        } catch (Exception e) {
            e.getMessage();
        }
        System.out.println("lastLine=" + lastLine);
        return lastLine;
    }

    public static byte[] readInputStream(InputStream inputStream) throws IOException {
        byte[] buffer = new byte[1024];
        int len = 0;
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try {
            while ((len = inputStream.read(buffer)) != -1) {
                bos.write(buffer, 0, len);
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
        bos.close();
        return bos.toByteArray();
    }

    private boolean interruptibleDownFile(String url, File saveDir, String d, String name) throws IOException {
        Future<String> future = null;
        final ExecutorService exec = Executors.newFixedThreadPool(1);
        boolean res = false;
        try {
            Callable<String> call = new Callable<String>() {
                public String call() throws Exception {
                    //开始执行耗时操作
                    URLConnection conn = new URL(url).openConnection();
                    conn.setRequestProperty("cookie", cookie);
                    InputStream InputStream = conn.getInputStream();
                    byte[] getData = readInputStream(InputStream);
                    File file = new File(saveDir + "/" + File.separator + d + "." + name);
                    FileOutputStream fos = new FileOutputStream(file);
                    fos.write(getData);
                    if (fos != null) {
                        fos.close();
                    }
                    if (InputStream != null) {
                        InputStream.close();
                    }
                    return "线程执行完成.";
                }
            };
            future = exec.submit(call);
            String obj = future.get(1000 * 5, TimeUnit.MILLISECONDS);
            System.out.println("任务成功返回:" + obj);
            res = true;
        } catch (TimeoutException ex) {
            System.out.println("处理超时啦....");
            ex.printStackTrace();
            future.cancel(true);
            System.out.println("请求是否打断:" + future.isCancelled());
        } catch (Exception e) {
            System.out.println("处理失败.");
            e.printStackTrace();
        } finally {
            exec.shutdownNow();
            /*while (!exec.isTerminated()) {
            }*/
            return res;
        }
    }

    private void downfile(String url, File saveDir, String d, String name) throws IOException {
        URLConnection conn = new URL(url).openConnection();
        conn.setRequestProperty("cookie", cookie);
        conn.setConnectTimeout(360 * 1000);
        InputStream InputStream = conn.getInputStream();
        byte[] getData = readInputStream(InputStream);
        File file = new File(saveDir + "/" + File.separator + d + "." + name);
        FileOutputStream fos = new FileOutputStream(file);
        fos.write(getData);
        if (fos != null) {
            fos.close();
        }
        if (InputStream != null) {
            InputStream.close();
        }
    }


    public static int isExitTable(String tableId) {
        Connection conn = null;
        int erasure = 0;
        Statement statement = null;
        try {
            Class.forName("org.postgresql.Driver");
            conn = DriverManager.getConnection("jdbc:postgresql://124.70.154.253:5432/qfx1203", "root", "hihidata@2020!");
            statement = conn.createStatement();
            ResultSet rs = statement.executeQuery("SELECT erasure FROM \"hi_conf_index\" where id like '" + tableId + "'");
            while (rs.next()) erasure = rs.getInt("erasure");

        } catch (ClassNotFoundException | SQLException e) {
            e.printStackTrace();
        }
        return erasure;
    }

}









