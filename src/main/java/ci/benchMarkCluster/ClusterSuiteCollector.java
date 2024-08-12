package ci.benchMarkCluster;

import base.http.JSchUtil;
import base.third.jsy.JSYTokenUtils;
import base.third.jsy.SuiteUtils;
import cn.hutool.core.io.FileUtil;
import com.jcraft.jsch.JSchException;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.ResponseBody;
import org.apache.commons.lang3.StringUtils;
import org.apache.log4j.*;

import java.io.*;
import java.text.SimpleDateFormat;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class ClusterSuiteCollector {
    private static final String logUrl = "https://jsy-log.jiushuyun.com/polars/metric/";
    private static final String logToken = "anN5MjAyMjpicG1mMjAyMg==";
    private static final String workDir = Optional.ofNullable(System.getProperty("workDir")).orElse("/opt/nxl/test/");
    private static final String suitePath = Optional.ofNullable(System.getProperty("suitePath")).orElse("/data/cluster_test/suite/");
    private static final int startHour = Integer.parseInt(Optional.ofNullable(System.getProperty("startHour")).orElse("0"));
    private static final int stopHour = Integer.parseInt(Optional.ofNullable(System.getProperty("stopHour")).orElse("23"));
    private static final String sessionHost = Optional.ofNullable(System.getProperty("sessionHost")).orElse("192.168.5.94");
    private static final String sessionUserName = Optional.ofNullable(System.getProperty("sessionUserName")).orElse("root");
    private static final String sessionPassword = Optional.ofNullable(System.getProperty("sessionPassword")).orElse("polars");
    private static final Integer memoryLimit = Integer.valueOf(Optional.ofNullable(System.getProperty("memoryLimit")).orElse("2000000000"));
    private static final JSchUtil jSchUtil = new JSchUtil();
    private static final OkHttpClient client = new OkHttpClient().newBuilder()
            .readTimeout(600, TimeUnit.SECONDS)
            .connectTimeout(60,TimeUnit.SECONDS)
            .build();
    private static final SuiteUtils suiteUtils = new SuiteUtils(client,jSchUtil);
    private static final Logger logger = Logger.getLogger(ClusterSuiteCollector.class);
    static {
        try {
            jSchUtil.initializeSession(sessionUserName,sessionHost,sessionPassword);
        } catch (JSchException e) {
            logger.error(e.getMessage(),e);
        }

    }

    private static Set<String> getWorkerName(){
        Set<String> result = new HashSet<>();
        Request request = new Request.Builder()
                .addHeader("accept","text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7")
                .addHeader("authorization","Basic "+logToken)
                .url(logUrl)
                .build();
        try {
            Response response = client.newCall(request).execute();
            if (response.body()!=null){
                String responseBody = Objects.requireNonNull(response.body()).string();
                logger.info(responseBody);
                result = parseWorkerNames(responseBody);
            }

        } catch (IOException e) {
            logger.error(e.getMessage(),e);
        }
        logger.info("查找到的worker:");
        for (String worker : result){
            logger.info("                "+worker);
        }
        return result;
    }


    private static long getYesterdayHour(int hour) {
        LocalDateTime now = LocalDateTime.now().minusDays(1); // 获取昨天日期时间
        LocalDateTime yesterdayHour = now.withHour(hour).withMinute(0).withSecond(0).withNano(0); // 获取昨天指定整点时间
        return yesterdayHour.toEpochSecond(ZoneOffset.ofHours(8)); // 转换为时间戳（以北京时间为准）
    }


    private static String getYesterdayDate(String pattern) {
        SimpleDateFormat sdf = new SimpleDateFormat(pattern);
        Calendar calendar = Calendar.getInstance();
        calendar.setTime(new Date());
        calendar.add(Calendar.DAY_OF_MONTH, -1);
        return sdf.format(calendar.getTime());
    }

    /**
     * *查找所有的worker,正则找不带fdb的
     */
    private static Set<String> parseWorkerNames(String html) {
        Set<String> workerNames = new HashSet<>();
        Pattern pattern = Pattern.compile("<a href=\"(polars-worker[^/]*[^fdb])/\">");
        Matcher matcher = pattern.matcher(html);
        while (matcher.find()) {
            if (!StringUtils.contains(matcher.group(1),"fdb")){
                workerNames.add(matcher.group(1));
            }
        }
        return workerNames;
    }

    /**
     *  下载metric文件的
     */
    private static String downloadFile(String url,String dirPath){
        String result;
        File dir = new File(dirPath);
        if (!dir.exists()) {
            dir.mkdirs(); // 创建目录及其所有父目录
        }
        String[] urlSplit = url.split("/");
        String filePath  = dirPath + urlSplit[urlSplit.length-1];
        if (FileUtil.exist(filePath)){
            logger.info(filePath + "重复，删除之前的");
            FileUtil.del(filePath);
        }
        logger.info("开始从"+url+"下载文件");
        Request request = new Request.Builder()
                .url(url)
                .addHeader("authorization","Basic "+logToken)
                .build();
        ResponseBody body = null;
        try {
            Response response = client.newCall(request).execute();

            body = response.body();
            InputStream inputStream = body != null ? body.byteStream() : null;
            BufferedInputStream bufferedInputStream = new BufferedInputStream(Objects.requireNonNull(inputStream));
            FileOutputStream fileOutputStream = new FileOutputStream(dirPath + urlSplit[urlSplit.length-1]);
            byte[] buffer = new byte[1024];
            int len;
            while ((len = bufferedInputStream.read(buffer)) != -1) {
                fileOutputStream.write(buffer, 0, len);
            }
            fileOutputStream.flush();
            fileOutputStream.close();
            bufferedInputStream.close();
        } catch (IOException e) {
            logger.error(e.getMessage(),e);
        }finally {
            if (body != null) {
                body.close();
            }
        }
        result = dirPath + urlSplit[urlSplit.length-1];
        return result;
    }

    private static void duplicateFile(String filePath){
        File directory = new File(filePath);
        if(!directory.isDirectory()){
            logger.info("The provided argument is not a directory.");
            return;
        }
        Map<String,File> fileSizes = new HashMap<>();
        for (File file: Objects.requireNonNull(directory.listFiles())){
            if (file.isFile() && file.getName().endsWith(".suite2")){
                String fileName = file.getAbsolutePath();
                String size = jSchUtil.execQueryList("unzip -l " + fileName + " | awk 'END {print $1}'").get(0);
                logger.info(fileName+"解压后大小为"+size);
                if (fileSizes.containsKey(size)){
                    File oldFile = fileSizes.get(size);
                    if (file.lastModified()>oldFile.lastModified()){
                        logger.info(fileName+"解压后大小与"+oldFile.getAbsolutePath()+"重复，自动删除");
                        FileUtil.del(file);
                    }else {
                        logger.info(fileName+"解压后大小与"+oldFile.getAbsolutePath()+"重复，自动删除"+oldFile.getAbsolutePath()+",因为这个文件比较新");
                        FileUtil.del(oldFile);
                        fileSizes.put(size,file);
                    }
                }else {
                    fileSizes.put(size,file);
                }
            }
        }
        jSchUtil.closeSession();
    }

    public static void main(String[] args) throws InterruptedException {
        // log4j配置
        ConsoleAppender consoleAppender = new ConsoleAppender();
        consoleAppender.setLayout(new PatternLayout("%d{yyyy-MM-dd HH:mm:ss.SSS} [%t] %-5p %c{1} - %m%n")); // 设置输出格式
        consoleAppender.activateOptions(); // 激活设置
        // 添加 ConsoleAppender 到根日志对象
        Logger.getRootLogger().removeAllAppenders();
        Logger.getRootLogger().addAppender(consoleAppender);

        Set<String> workerNames = getWorkerName();
        String token = JSYTokenUtils.getToken("17798800686","58342And5306");
        ExecutorService executor = Executors.newFixedThreadPool(workerNames.size());
        for (String workName : workerNames){
            executor.execute(() -> {
                String downloadUrl = logUrl +workName + "/" + getYesterdayDate("yyyy-MM") + "/operator_calculate-" + getYesterdayDate("yyyy-MM-dd") +".log.gz";
                String dirPath = workDir + "/metric_for_work/" + workName + "/" +getYesterdayDate("yyyy-MM-dd") + "/";
                String filePath = downloadFile(downloadUrl , dirPath);
                List<String> taskList = jSchUtil.execQueryList("zgrep \"peakUserMemory=\" " + filePath + " | awk -F \",\" '/peakUserMemory/ {split($5, a, \"=\"); if (a[2] > "+memoryLimit+") {print $0}}'");
                logger.info("taskList.size()="+taskList.size());
                int i = 0;
                for (String task : taskList){
                    String taskName = task.split("_job_")[1].split("',")[0];
                    String createTimeStamp = task.split("createTime=")[1].split(",")[0];
                    long createTime = Long.parseLong(createTimeStamp) / 1000L;
                    if (createTime >= getYesterdayHour(startHour) && createTime <= getYesterdayHour(stopHour)){
                        try {
                            long startTime = System.currentTimeMillis();
                            suiteUtils.importSuiteToBenchmark("https://work.jiushuyun.com/decision/v1/engine/polars/download-suite?tenant="+taskName+"&plsPath=polars/pls/"+taskName+".pls"
                                    ,taskName,suitePath,taskName+".suite2",token);
                            long endTime = System.currentTimeMillis();
                            long elapsedTime = endTime - startTime;
                            logger.info(task+" download run time: " + elapsedTime + "ms");
                            i++;
                        } catch (IOException | InterruptedException e) {
                            logger.error(e.getMessage(),e);
                        }
                    } else if (createTime > getYesterdayHour(stopHour)){
                        logger.info("createTime="+createTime+", getYesterdayHour(startHour)="+getYesterdayHour(startHour)+", getYesterdayHour(stopHour)="+getYesterdayHour(stopHour));
                        break;
                    }
                }
                logger.info("Thread " + Thread.currentThread().getId() + " has completed.");
                logger.info("总共导入suite数目为:"+i);
            });
        }
        executor.shutdown();
        boolean allThreadsCompleted = executor.awaitTermination(16, TimeUnit.HOURS);
        if (allThreadsCompleted) {
            logger.info("All threads have completed.");
        } else {
            logger.info("Some threads have not completed within 16 HOURS.");
        }
        duplicateFile(suitePath);
        jSchUtil.closeSession();
    }


}
