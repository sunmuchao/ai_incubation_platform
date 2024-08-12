package ci.benchMark;

import base.http.JSchUtil;
import com.jcraft.jsch.JSchException;
import com.jcraft.jsch.Session;

import java.io.*;
import java.net.URLEncoder;
import java.text.SimpleDateFormat;
import java.util.*;


public class MetricUtil {

    public final static String metricFilePath = "/data/ContinuousIntegration/polars_test-benchmark/home/metric/";
    public final static String metricFileNamePrefix = "operator_calculate";
    public final static String metricDictFilePath = "/data/ContinuousIntegration/polars_test-benchmark/home_dict/metric/";
    public final static String metricCppFilePath = "/data/ContinuousIntegration/polars_test-benchmark/home/metric/";
    public final static String metricCppDictFilePath = "/data/ContinuousIntegration/polars_test-benchmark/home/metric/";


    /**
     * 获得metric用，实际上是获得了metric写入文件再将文件暴露出来
     *
     * @param data 报告中的某行数据
     * @param pros 报告的第一行，用来根据caseName等拿列号用
     * @param pr   pr对象，放了这个pr的信息
     * @return 该行metric存放地址
     */
    public static String getMetric(String[] data, List<String> pros, PR pr) {
        String dataType = pr.getTask().getDataTypes()[0];
        String branch = pr.getDisplayId();
        Map<String, Integer> properties = getIndex(pros);
        if ((properties == null) || (properties.isEmpty()) || (data == null) || (data.length < properties.size() - 1)) {
            return "error 数据检验错误";
        }
        int taskIdPosition = properties.get("caseName"), startTimeStampPosition = properties.get("startTime"),
                stopTimeStampPosition = properties.get("endTime"), categoryEpoch = properties.get("categoryEpoch");

        String startTimeStampString = data[startTimeStampPosition], stopTimeStampString = data[stopTimeStampPosition],
                taskId = data[taskIdPosition], categoryEpochString = data[categoryEpoch],
                filePath = "metric_file/" + taskId + categoryEpochString + ".metric";

        File file = new File(BanchMarckParser.curpath + filePath);
        if (file.exists()) {
//            System.out.println("文件已存在，直接使用");
            return filePath;
        }

        long startTimeStamp, stopTimeStamp;
        if (!isNumber(startTimeStampString)) {
            startTimeStamp = Long.parseLong(startTimeStampString);
        } else {
            //           System.out.println("startTimeStampString="+startTimeStampString);
            return "error 无效的时间戳（开始）";
        }
        if (!isNumber(stopTimeStampString)) {
            stopTimeStamp = Long.parseLong(stopTimeStampString);
        } else {
            //          System.out.println("stopTimeStampString="+stopTimeStampString);
            return "error 无效的时间戳（结束）";
        }
        List<String> list = null;
        Session session = null;
        JSchUtil jSchUtil = new JSchUtil();
        Map<String, String> time = getFile(dataType, startTimeStamp, stopTimeStamp, branch);
        if (time == null) {
            return "error time == null";
        }
        String name = time.get("name");
        String path = time.get("path");
        try {
            session = jSchUtil.initializeSession("root", "192.168.101.29", "Fr@2023");
            list = getAllData(jSchUtil, taskId, path, name, startTimeStamp, stopTimeStamp);
        } catch (JSchException e) {
            e.printStackTrace();
        } finally {
            if (session != null) {
                jSchUtil.closeSession();
            }
        }
        try {
            StringBuilder sb = new StringBuilder();
            if (list == null || list.isEmpty()) return "error 未获得metric";
            for (String s : list) {
                sb.append(s);
                sb.append("\n\n\n");
            }
//            System.out.println("开始写文件");
            mBufferedWriter(BanchMarckParser.curpath + filePath, sb.toString());
        } catch (IOException e) {
            e.printStackTrace();
        }
//        System.out.println(filePath);
        try {
            filePath = URLEncoder.encode(filePath, java.nio.charset.StandardCharsets.UTF_8.toString()).replace("%2F", "/").replace("#", "%23");
        } catch (UnsupportedEncodingException e) {
            e.printStackTrace();
        }
        return filePath;
    }


    /**
     * 获得html页中的列号。用来看caseName等列的列号
     *
     * @param propers 就是 propers
     * @return 返回值是用来拿caseName等参数的index的
     */
    private static Map<String, Integer> getIndex(List<String> propers) {
        if ((propers == null) || (propers.size() == 0)) return null;
        Map<String, Integer> result = new HashMap<>();
        for (int i = 0; i < propers.size(); i++) {
            result.put(propers.get(i), i);
        }
        return result;
    }


    /**
     * 得到当前两个时间点对应的文件
     *
     * @param startTimeStamp 开始时间
     * @param stopTimeStamp  结束时间
     * @return 一个map，保存了文件路径和名字
     */
    private static Map<String, String> getFile(String dataType, long startTimeStamp, long stopTimeStamp, String branch) {
        Map<String, String> map = new HashMap<>();
        SimpleDateFormat formatter = new SimpleDateFormat("yyyy-MM-dd");
        SimpleDateFormat formatter2 = new SimpleDateFormat("yyyy-MM");
        Date startDate = new Date(startTimeStamp);
        Date stopDate = new Date(stopTimeStamp);
        Date nowDate = new Date();
        String startTime = formatter.format(startDate);
        String stopTime = formatter.format(stopDate);
        String nowTime = formatter.format(nowDate);
//        System.out.println("startTime: "+startTime+"stopTime: "+stopTime+"nowTime: "+nowTime);
        /*if (StringUtils.isNullOrEmpty(startTime) || StringUtils.isNullOrEmpty(stopTime)) {
            return null;
        }*/
        if (startTime.equals(stopTime)) {
            if (startTime.equals(nowTime)) {
                if ("dict".equals(dataType) && "feature/polars-llvm".equals(branch)) {
                    map.put("path", MetricUtil.metricCppDictFilePath);
                } else if ("normal".equals(dataType) && "feature/polars-llvm".equals(branch)) {
                    map.put("path", MetricUtil.metricCppFilePath);
                } else if ("dict".equals(dataType)) {
                    map.put("path", MetricUtil.metricDictFilePath);
                } else if ("normal".equals(dataType)) {
                    map.put("path", MetricUtil.metricFilePath);
                }
                map.put("name", MetricUtil.metricFileNamePrefix + ".log");
            } else {
                if ("dict".equals(dataType) && "feature/polars-llvm".equals(branch)) {
                    map.put("path", MetricUtil.metricCppDictFilePath + formatter2.format(startDate));
                } else if ("normal".equals(dataType) && "feature/polars-llvm".equals(branch)) {
                    map.put("path", MetricUtil.metricCppFilePath + formatter2.format(startDate));
                } else if ("dict".equals(dataType)) {
                    map.put("path", MetricUtil.metricDictFilePath + formatter2.format(startDate));
                } else if ("normal".equals(dataType)) {
                    map.put("path", MetricUtil.metricFilePath + formatter2.format(startDate));
                }
                map.put("name", MetricUtil.metricFileNamePrefix + "-" + startTime + ".log.gz");
            }
        }
        return map;
    }


    /**
     * 根据taskId获得当前task的所有metric
     *
     * @param taskId         taskId
     * @param metricFilePath metric文件的路径
     * @param metricFileName metric文件的名字
     * @param startTime      整个jsy任务的开始时间
     * @param stopTime       整个jsy任务的结束时间
     * @return metric记录
     */
    private static List<String> getAllData(JSchUtil jSchUtil, String taskId, String metricFilePath, String metricFileName, long startTime, long stopTime) {
        //if (StringUtils.isNullOrEmpty(metricFileName) ||StringUtils.isNullOrEmpty(metricFilePath)||StringUtils.isNullOrEmpty(taskId)){
        //return null;
        //}
        if (jSchUtil.getSession() == null) {
            System.out.println("jSchUtil.getSession()==null");
            return null;
        }
        List<String> list = new ArrayList<>();
        String cdCommand = String.format("cd %s", metricFilePath);
        final String queryCommand = String.format("zgrep \"taskName='%s*\" %s", taskId, metricFileName);
        String command = cdCommand + ";" + queryCommand + ";" + "exit";
        List<String> queryList = jSchUtil.execQueryList(command);
        for (String s : queryList) {
            String createTime = s.split("createTime=")[1].split(",")[0];
            String endTime = s.split("endTime=")[1].split("]")[0];
            if (isNumber(createTime) || isNumber(endTime)) {
                continue;
            }
//            System.out.println("createTime = " + createTime + ";  endTime = " + endTime+ ";  isInTime(startTime,stopTime,createTime,endTime)" +isInTime(startTime,stopTime,createTime,endTime));
            if (isInTime(startTime, stopTime, createTime, endTime)) {
                String taskName = s.split("taskName='")[1].split("'")[0];
                String singleData = getSingleData(jSchUtil, taskName, metricFilePath, metricFileName);
                list.add(singleData);
            }
        }
        return list;
    }


    /**
     * 得到单个的metric数据
     *
     * @param taskId         任务id,前置步骤已经拿到的全名
     * @param metricFilePath metric文件的路径
     * @param metricFileName metric文件的名字
     * @return 当前的metric日志
     */
    private static String getSingleData(JSchUtil jSchUtil, String taskId, String metricFilePath, String metricFileName) {
        /*if (StringUtils.isNullOrEmpty(metricFileName) || StringUtils.isNullOrEmpty(metricFilePath) || StringUtils.isNullOrEmpty(taskId)) {
            return null;
        }*/
        if (jSchUtil.getSession() == null) {
            System.out.println("jSchUtil.getSession()==null");
            return null;
        }
        String cdCommand = String.format("cd %s", metricFilePath);
        final String queryCommand = String.format("zgrep -A 5000 '%s' %s  | sed -n '1,/^.*Job:.*$/p' | head -n -1", taskId, metricFileName);
        String command = cdCommand + ";" + queryCommand + ";" + "exit";
        return jSchUtil.execQuery(command);
    }


    /**
     * 写数据
     *
     * @param filepath 文件路径
     * @param content  写的内容
     * @throws IOException 抛错给上层
     */
    private static void mBufferedWriter(String filepath, String content) throws IOException {
        try (BufferedWriter bufferedWriter = new BufferedWriter(new FileWriter(filepath))) {
            bufferedWriter.write(content);
        }
    }


    /**
     * 判断字符串是不是一个非空的可以转化为int或long的数字
     *
     * @param s 输入的字符串
     * @return 返回true或者false
     */
    private static boolean isNumber(String s) {
        //return !StringUtils.isStrictlyNumeric(s) || (StringUtils.isNullOrEmpty(s));
        return false;
    }

    /**
     * 判断metric中的时间是不是在界面上的时间范围内，在的话就将这个metric取出来
     *
     * @param startTime 界面上的开始时间
     * @param stopTime  界面上的结束时间
     * @param creatTime metric中的开始时间
     * @param endTime   metric中的结束时间
     * @return true或者false
     */
    private static boolean isInTime(long startTime, long stopTime, String creatTime, String endTime) {

        return (startTime < Long.parseLong(creatTime)) && (startTime < Long.parseLong(endTime)) &&
                (stopTime > Long.parseLong(creatTime)) && (stopTime > Long.parseLong(endTime));
    }

}