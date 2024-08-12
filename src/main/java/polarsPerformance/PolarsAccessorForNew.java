package polarsPerformance;

import base.db.DBUtils;
import base.http.HttpUtils;
import base.http.JSchUtil;
import base.third.jsy.JSYTokenUtils;
import base.third.jsy.SuiteUtils;
import cn.hutool.core.io.FileUtil;
import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONException;
import com.alibaba.fastjson.JSONObject;
import com.jcraft.jsch.JSchException;
import okhttp3.OkHttpClient;
import org.apache.commons.lang3.StringUtils;
import org.apache.log4j.ConsoleAppender;
import org.apache.log4j.Logger;
import org.apache.log4j.PatternLayout;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.TimeUnit;

public class PolarsAccessorForNew {

    private static final Logger logger = Logger.getLogger(PolarsAccessorForNew.class);
    private final static String jarVersion = Optional.ofNullable(System.getProperty("jarVersion")).orElse("3.6.5");
    private final static String binHomePath = "/opt/nxl/PolarsAccessorsNew";
    private final static String downloadPath = "http://192.168.5.94:8082/PolarsAccessorsNew";
    private final static String metricDownloadPath = downloadPath + "/metricFile";
    private final static String suiteDownloadPath = downloadPath + "/suite/" + jarVersion;
    private final static String traceDownloadPath = downloadPath + "/traceFile";
    private final static String jmeterBinPath = binHomePath + "/apache-jmeter-5.4.1/bin/";
    private final static String jmeterPath = binHomePath + "/jsytest.jmx";
    private final static String traceIdPath = binHomePath + "/traceId";
    private final static String traceFilePath = binHomePath + "/traceFile";
    private final static String metricFilePath = binHomePath + "/metricFile";
    private final static String suiteFilePath = binHomePath + "/suite/" + jarVersion;
    private final static String execDay=new SimpleDateFormat("yyyy-MM-dd").format(new Date());
    private final static String jtlFilePath = binHomePath + "/jtl/jsytest-"+ execDay + ".jtl";
    private static String token = null;
//    private static boolean needToDownloadSuite = false;
    private static final OkHttpClient client = new OkHttpClient().newBuilder()
            .readTimeout(15, TimeUnit.MINUTES)
            .connectTimeout(15,TimeUnit.MINUTES)
            .build();
    private static final JSchUtil jSchUtil = new JSchUtil();
    private static final SuiteUtils suiteUtils = new SuiteUtils(client,jSchUtil);
    static {
        try {
            jSchUtil.initializeSession("root","192.168.5.94","polars");
        } catch (JSchException e) {
            logger.error(e.getMessage(),e);
        }

    }

//    private final static String jmeterBinPath = "C:/Users/n1776/Desktop/test/apache-jmeter-5.4.1/bin/";
//    private final static String jmeterPath = "C:/Users/n1776/Desktop/test/jsytest.jmx";
//    private final static String traceIdPath = "C:/Users/n1776/Desktop/test/traceId";
//    private final static String traceFilePath = "C:/Users/n1776/Desktop/test/traceFile";
//    private final static String execDay=new SimpleDateFormat("yyyy-MM-dd").format(new Date());
//    private final static String jtlFilePath = "C:/Users/n1776/Desktop/test/jtl/jsytest-"+ execDay + ".jtl";
//    private final static String metricFilePath = "C:/Users/n1776/Desktop/test/metricFile";
//    private static String token = null;


    public static void main(String[] args) throws IOException, InterruptedException {
        // log4j配置
        ConsoleAppender consoleAppender = new ConsoleAppender();
        consoleAppender.setLayout(new PatternLayout("%d{yyyy-MM-dd HH:mm:ss.SSS} [%t] %-5p %c{1} - %m%n")); // 设置输出格式
        consoleAppender.activateOptions(); // 激活设置
        // 添加 ConsoleAppender 到根日志对象
        Logger.getRootLogger().removeAllAppenders();
        Logger.getRootLogger().addAppender(consoleAppender);

        logger.info("开始执行,当前时间:" + new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new Date()));
        logger.info("当前版本的版本号为:"+jarVersion);
        prepareEnv();
//        String sql = "select * from `jsyFormalPerformanceForNew` where jarVersion='"+jarVersion+"'";
//        List<Map<String, String>> query = DBUtils.query(sql);
//        if (query.isEmpty()) needToDownloadSuite = true;
        runJmeter();
        token = JSYTokenUtils.getToken("15069244033", "Maxnxl555!");
        List<JsySqlPerformanceForNew> allProfileList = new ArrayList<>();
        List<JsySqlPerformanceForNew> caseList = analysisResultFile();
        for (JsySqlPerformanceForNew casePerformance :caseList){
            if ("fail".equals(casePerformance.getTraceId())){
                casePerformance.setRunTime(casePerformance.getResponseTime());
                insertData(casePerformance);
            }else {
                List<JsySqlPerformanceForNew> profileList = analysisAndDownloadTrace(casePerformance);
                logger.info(casePerformance.getCaseName() +"的profileList.size()="+profileList.size());
                for (JsySqlPerformanceForNew performance:profileList){
                    analysisProfile(performance);
                    performance.setTraceDownloadPath(traceDownloadPath + "/" + performance.getTraceId() + ".json");
                    allProfileList.add(performance);
                }
            }
        }
        List<JsySqlPerformanceForNew> filteredList = filterTraceId(allProfileList);
        logger.info("filteredList.size() = "+filteredList.size()+" , allProfileList.size() = "+allProfileList.size());

        //下载suite和metric，suite必须要后下载，不然会因为时间问题找不到profile
        for (JsySqlPerformanceForNew performance:filteredList){
            downloadMetric(performance);
            performance.setMetricDownloadPath(metricDownloadPath + "/" + performance.getTraceId() + "-"+ performance.getTaskName() + ".metric");
            String caseName = performance.getCaseName().replace("&","");
            if (!FileUtil.exist(suiteFilePath + "/" + caseName+".suite2")){
                suiteUtils.importSuiteToBenchmark("https://work.jiushuyun.com/decision/v1/engine/polars/download-suite?tenant="+performance.getTaskName()+"&plsPath=polars/pls/"+performance.getTaskName()+".pls",
                        performance.getTaskName(),suiteFilePath,caseName+".suite2",token);
            }
            performance.setSuiteDownloadPath(suiteDownloadPath+"/"+caseName+".suite2");
            insertData(performance);
        }
        jSchUtil.closeSession();
        logger.info("执行结束,当前时间:" + new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new Date()));

    }

    /**
     * *过滤一下计算，有一些trace里面既有计算又有count，只拿计算的taskName，不然结果理解难度大
     */
    public static List<JsySqlPerformanceForNew> filterTraceId(List<JsySqlPerformanceForNew> objects) {
        Map<String, JsySqlPerformanceForNew> traceIdMap = new HashMap<>();
        List<JsySqlPerformanceForNew> resultList = new ArrayList<>();

        for (JsySqlPerformanceForNew object : objects) {
            String traceId = object.getTraceId();

            if ("fail".equalsIgnoreCase(traceId)) {
                resultList.add(object);
            } else {
                if (!traceIdMap.containsKey(traceId)) {
                    traceIdMap.put(traceId, object);
                } else {
                    JsySqlPerformanceForNew existingObject = traceIdMap.get(traceId);
                    LocalDateTime existingTime = parseDateTime(existingObject.getCreateTime());
                    LocalDateTime currentTime = parseDateTime(object.getCreateTime());
                    if (currentTime.isBefore(existingTime)) {
                        traceIdMap.put(traceId, object);
                    }
                }
            }
        }
        resultList.addAll(traceIdMap.values());
        return resultList;
    }


    private static LocalDateTime parseDateTime(String dateTimeString) {
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
        return LocalDateTime.parse(dateTimeString.split("\\.")[0], formatter);
    }

    private static byte[] readInputStream(InputStream inputStream) throws IOException {
        byte[] buffer = new byte[1024];
        int len = 0;
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        while ((len = inputStream.read(buffer)) != -1) {
            bos.write(buffer, 0, len);
        }
        bos.close();
        return bos.toByteArray();
    }

    private static long convertToTimestamp(String str) {
        SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");
        Date date = null;
        try {
            date = dateFormat.parse(str);
        } catch (ParseException e) {
            logger.error(e.getMessage(),e);
        }
        if (date != null) {
            return date.getTime();
        }else {
            return System.currentTimeMillis();
        }
    }

    private static void downloadMetric(JsySqlPerformanceForNew performance) {
        if (StringUtils.isEmpty(performance.getWorkNode()) || StringUtils.isEmpty(performance.getTaskName())){
            logger.info("以下变量为空,不下载metric！performance.getWorkNode() = "+performance.getWorkNode()+";performance.getTaskName()="+performance.getTaskName());
            return;
        }
        String fileUrl = "https://work.jiushuyun.com/decision/v1/engine/polars/download-metric" +
                "?tenant=" +
                performance.getTaskName() +
                "&nodeName=" +
                StringUtils.split(performance.getWorkNode(), "(")[0] +
                "&taskId=" +
                performance.getTaskName() +
                "&submit=" +
                convertToTimestamp(performance.getCreateTime());
        String savePath = metricFilePath + "/" + performance.getTraceId() + "-"+ performance.getTaskName() + ".metric";
        try {
            URL url = new URL(fileUrl);
            HttpURLConnection conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setRequestProperty("cookie","tenantId=7ad5219f-8342-4a1c-b6d6-51ea2b6ea2b6; fine_remember_login=-1; fr_id_appname=jiushuyun; fine_auth_token=" + token);
            conn.setConnectTimeout(5 * 1000);
            InputStream inputStream = conn.getInputStream();
            byte[] getData = readInputStream(inputStream);

            // 将文件保存到本地
            File saveDir = new File(savePath.substring(0, savePath.lastIndexOf("/")));
            if (!saveDir.exists()) {
                saveDir.mkdirs();
            }
            File file = new File(savePath);
            FileOutputStream fos = new FileOutputStream(file);
            fos.write(getData);
            fos.close();
            inputStream.close();
            logger.info("metric"+savePath+"下载成功！");
        } catch (Exception e) {
            logger.error(e.getMessage(),e);
            logger.info("metric"+savePath+"下载失败！");
        }

    }


    private static void prepareEnv(){
        if (FileUtil.exist(jtlFilePath)){
            FileUtil.del(jtlFilePath);
            logger.info(jtlFilePath + ": 日志文件已存在，开始删除此文件（同一天只保留一份）");
        }
        if (FileUtil.exist(traceIdPath)){
            logger.info("开始清理"+traceIdPath);
            FileUtil.writeUtf8String("", traceIdPath);
        }else {
            FileUtil.touch(traceIdPath);
        }
        logger.info("开始清理数据库中多余数据");
        String sql = "delete from jsyFormalPerformanceForNew where date='"+execDay+"'";
        logger.info("共删除数据库中多余数据" + DBUtils.updateData(sql) +"条");
    }



    private static void runJmeter() throws IOException, InterruptedException {
        Process process = Runtime.getRuntime().exec(jmeterBinPath + "jmeter" +
                " -n -t " + jmeterPath + " -l " + jtlFilePath);
        logger.info(
                "jmeter执行命令:" +
                        jmeterBinPath + "jmeter" +
                        " -n -t " + jmeterPath + " -l " + jtlFilePath);
        process.waitFor();
    }

    //解析jmeter脚本
    private static List<JsySqlPerformanceForNew> analysisResultFile() throws IOException {
        List<JsySqlPerformanceForNew> result = new ArrayList<>();
        JsyFileReader reader = new JsyFileReader(new File(traceIdPath));
        StringBuffer sb = reader.readAfterCleanUp();
        logger.info(sb);
        String[] s = sb.toString().split("\n");
        for (String value : s) {
            JsySqlPerformanceForNew performance;
            String id = value.split(",")[0];
            if (id.contains("_")){
                performance = JsySqlPerformanceForNew.builder()
                        .traceId(value.split(",")[1])
                        .id(id)
                        .caseName(id.split("_")[0])
                        .responseTime(value.split(",")[2])
                        .isSuccessful(value.split(",")[3])
                        .currentTime(value.split(",")[4])
                        .date(execDay)
                        .build();
            }else {
                performance = JsySqlPerformanceForNew.builder()
                        .traceId(value.split(",")[1])
                        .id(id)
                        .caseName(id)
                        .responseTime(value.split(",")[2])
                        .isSuccessful(value.split(",")[3])
                        .currentTime(value.split(",")[4])
                        .date(execDay)
                        .build();
            }
            if("null".contains(performance.getTraceId())){
                logger.info(performance.getCaseName() + "的TraceId为空");
                continue;
            }
            result.add(performance);
        }
        return result;
    }


    private static List<JsySqlPerformanceForNew> analysisAndDownloadTrace(JsySqlPerformanceForNew jsySqlPerformanceForNew){
        List<JsySqlPerformanceForNew> list = new ArrayList<>();
        Set<String> taskNames = new HashSet<>();
        String url = "https://work.jiushuyun.com/decision/zipkin/api/v2/trace/" + jsySqlPerformanceForNew.getTraceId();
        HttpUtils httpUtils = new HttpUtils(url, "tenantId=7ad5219f-8342-4a1c-b6d6-51ea2b6ea2b6; fine_remember_login=-1; fr_id_appname=jiushuyun; fine_auth_token=" + token);
        String response = null;
        try {
            response = httpUtils.connectAndGetRequest();
            int retryTimes=3;
            while ((response != null && response.equals("[]") ||
                    (httpUtils.getResponseCode() == 503) ||
                    (response != null && response.contains("503 Service Unavailable")))
            && (retryTimes>0)) {
                logger.info(response);
                retryTimes--;
                response = httpUtils.connectAndGetRequest();
            }
        } catch (IOException e) {
            logger.error(e.getMessage(),e);
        }

        //analysis
        JSONArray jsonArray = null;
        try{
            jsonArray = JSON.parseArray(response);
        }catch (JSONException e){
            logger.error(e.getMessage(),e);
        }
        if (!Objects.isNull(jsonArray)){
            for (int k = 0; k < jsonArray.size(); k++) {
                JSONObject jsonObject = jsonArray.getJSONObject(k);
                if (jsonObject.getString("tags") != null) {
                    JSONObject tags = jsonObject.getJSONObject("tags");
                    String taskName = tags.getString("taskName");
                    if (taskName!=null && !taskNames.contains(taskName)){
                        JsySqlPerformanceForNew performance = JsySqlPerformanceForNew.builder()
                                .traceId(jsySqlPerformanceForNew.getTraceId())
                                .caseName(jsySqlPerformanceForNew.getCaseName())
                                .responseTime(jsySqlPerformanceForNew.getResponseTime())
                                .taskName(taskName)
                                .date(execDay)
                                .isSuccessful(jsySqlPerformanceForNew.getIsSuccessful())
                                .currentTime(jsySqlPerformanceForNew.getCurrentTime())
                                .id(jsySqlPerformanceForNew.getId())
                                .build();
                        list.add(performance);
                        taskNames.add(taskName);
                    }
                }
            }
        }

        //download
        String file = traceFilePath + "/" + jsySqlPerformanceForNew.getTraceId() + ".json";
        if (FileUtil.exist(file)){
            logger.info("文件" + file + "已经存在，删除后重新下载");
            FileUtil.del(file);
        }
        FileUtil.writeString(response,new File(file), StandardCharsets.UTF_8);

        return list;
    }



    //解析profile
    private static void analysisProfile(JsySqlPerformanceForNew performance){
        HttpUtils httpUtil = new HttpUtils("https://work.jiushuyun.com/decision/v1/polars/cluster/profile", "tenantId=7ad5219f-8342-4a1c-b6d6-51ea2b6ea2b6; fine_remember_login=-1; fr_id_appname=jiushuyun; fine_auth_token=" + token);
        String sql = "{\"sql\":\" select * from TaskInfoTable where name='" + performance.getTaskName() + "'\"}";
        logger.info("profile sql = "+sql);
        String profileResponse = httpUtil.connectAndGetPostRequest(sql);
        logger.info("======================================");
        logger.info("profileResponse = " + profileResponse);
        logger.info("======================================");
        if (profileResponse.split("\n").length == 2){
            String[] polarsData = profileResponse.split("\n")[1].split(" , ");
            performance.setStatus(polarsData[1]);
            performance.setType(polarsData[2]);
            performance.setCreateTime(polarsData[3]);
            performance.setEndTime(polarsData[4]);
            performance.setQueueTime(polarsData[5]);
            performance.setWaitResourceTime(polarsData[6]);
            performance.setPlanTime(polarsData[7]);
            performance.setStartTime(polarsData[8]);
            performance.setRunTime(polarsData[9]);
            performance.setFinishTime(polarsData[10]);
            performance.setExecutionAllTime(polarsData[11]);
            performance.setMemPeak(polarsData[12]);
            performance.setMemCurrent(polarsData[13]);
            performance.setWorkNode(polarsData[16]);
        }
    }


    //上传数据库
    private static void insertData(JsySqlPerformanceForNew performance){
        String sql = generateInsertSql(performance);

        if (DBUtils.updateData(sql)>0){
            logger.info("插入数据成功");
        }else {
            logger.info("插入数据失败！");
        }

    }


    private static String generateInsertSql(JsySqlPerformanceForNew obj) {

        return "INSERT INTO `jsyFormalPerformanceForNew` (id, taskName, caseName, traceId, date, status, type, createTime, endTime, responseTime, queueTime, waitResourceTime, planTime, startTime, runTime, finishTime, executionAllTime, memPeak, memCurrent, workNode, metricDownloadPath, traceDownloadPath, suiteDownloadPath, jarVersion, isSuccessful, currentTime) VALUES (" +
                "'" + obj.getId() + "'," +
                "'" + obj.getTaskName() + "'," +
                "'" + obj.getCaseName() + "'," +
                "'" + obj.getTraceId() + "'," +
                "'" + obj.getDate() + "'," +
                "'" + obj.getStatus() + "'," +
                "'" + obj.getType() + "'," +
                "'" + obj.getCreateTime() + "'," +
                "'" + obj.getEndTime() + "'," +
                "'" + obj.getResponseTime() + "'," +
                "'" + obj.getQueueTime() + "'," +
                "'" + obj.getWaitResourceTime() + "'," +
                "'" + obj.getPlanTime() + "'," +
                "'" + obj.getStartTime() + "'," +
                "'" + obj.getRunTime() + "'," +
                "'" + obj.getFinishTime() + "'," +
                "'" + obj.getExecutionAllTime() + "'," +
                "'" + obj.getMemPeak() + "'," +
                "'" + obj.getMemCurrent() + "'," +
                "'" + obj.getWorkNode() + "'," +
                "'" + obj.getMetricDownloadPath() + "'," +
                "'" + obj.getTraceDownloadPath() + "'," +
                "'" + obj.getSuiteDownloadPath() + "'," +
                "'" + jarVersion + "'," +
                "'" + obj.getIsSuccessful() + "'," +
                "'" + obj.getCurrentTime() + "'" +
                ")";
    }


}
