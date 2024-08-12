package polarsPerformance;

import base.http.HttpUtils;
import base.third.jsy.JSYTokenUtils;
import base.third.wechat.WechatMessageUtils;
import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.opencsv.CSVWriter;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang3.StringUtils;
import base.db.DBUtils;

import java.io.*;
import java.text.SimpleDateFormat;
import java.util.*;

public class PolarsAccessor {

//    static String jmeterBinPath = "C:/Users/n1776/办公/jmeter/apache-jmeter-5.4.1/bin/";
//    static String jmeterPath = "C:/Users/n1776/Desktop/jsytest.jmx";
//    static String traceIdPath = "D:/traceId";
//    static final String CSVFile="D:/";
    static String jmeterBinPath = "/opt/nxl/PolarsAccessors/apache-jmeter-5.4.1/bin/";
    static String jmeterPath = "/opt/nxl/PolarsAccessors/jsytest.jmx";
    static final String CSVFile="/opt/nxl/PolarsAccessors/result/";
    static String traceIdPath = "/opt/nxl/PolarsAccessors/traceId";
    static String afterDay=new SimpleDateFormat("yyyy-MM-dd").format(new Date());
    static String beforeDay="";
    static final String key="3a0c7517-9ce6-48fc-8ded-f4b4ea546c03";
    static int fallCaseCount=0,increaseCaseCount=0,newCaseCount=0,unchangedCaseCount=0;
    static Map<String,String> responseTimeMap = new HashMap<>();

    public static void main(String[] args) throws IOException {

        try {

            //执行jmeter
            Process process = Runtime.getRuntime().exec(jmeterBinPath + "jmeter" +
                    " -n -t " + jmeterPath + " -l " + jmeterBinPath + "jsytest.jtl");
            System.out.println(
                    "jmeter执行命令:" +
                            jmeterBinPath + "jmeter" +
                            " -n -t " + jmeterPath + " -l " + jmeterBinPath + "jsytest.jtl");

            process.waitFor();
            JsyFileReader reader = new JsyFileReader(new File(traceIdPath));
            StringBuffer sb = reader.readAfterCleanUp();
            System.out.println(sb.toString());
            String[] s = sb.toString().split("\n");
            jsyPerformance jp = new jsyPerformance();
            for (int i = 0; i < s.length; i++) {
                System.out.println("traceId=" + s[i].split(",")[1]);
                System.out.println("caseName=" + s[i].split(",")[0]);
                System.out.println("请求响应时间="+s[i].split(",")[2]);
                responseTimeMap.put(s[i].split(",")[1],s[i].split(",")[2]);
                jp.addCase(new Case(s[i].split(",")[1], s[i].split(",")[0]));
            }
            System.out.println("删除当天数据，共删除"+deleteAfterDayData(afterDay)+"行");
            System.out.println("删除当天结果表中数据，共删除"+deleteLastDayResultData()+"行");
            accessPolars(jp);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        try {
            Map<String, List<JsySqlPerformance>> afterDayMap = groupList(queryTime(afterDay));
            List<JsySqlPerformance> list = new ArrayList<>();
            List<JsySqlPerformance> fallCaseList = new ArrayList<>();
            List<JsySqlPerformance> increaseCaseList = new ArrayList<>();
            List<JsySqlPerformance> newList = new ArrayList<>();
            Map<String, String> earlyTimeMap = queryEarlyTime();
            for (Map.Entry<String, List<JsySqlPerformance>> next : afterDayMap.entrySet()) {
                String caseName = next.getKey();
                List<JsySqlPerformance> afterList = next.getValue();
                double afterAverageValue = getAverageValue(afterList);
                beforeDay = earlyTimeMap.get(caseName);
                if (beforeDay == null || beforeDay.isEmpty() || beforeDay.equals(afterDay)) {
                    System.out.println("新用例\""+caseName+"\",平均耗时为"+afterAverageValue);
                    newCaseCount++;
                    newList.addAll(afterList);
                    insertResult(caseName,"0000-00-00", "",afterDay, String.valueOf(afterAverageValue),"true","","");
                } else {
                    Map<String, List<JsySqlPerformance>> beforeDayMap = groupList(queryTime(beforeDay));
                    List<JsySqlPerformance> beforeList = beforeDayMap.get(caseName);
                    double beforeAverageValue = getAverageValue(beforeList);
                    int unchanged = isUnchanged(beforeAverageValue, afterAverageValue, 0.2);
                    String changeRange = String.format("%.2f",((afterAverageValue - beforeAverageValue) / beforeAverageValue)*100)+"%";
                    if (unchanged==-1){
                        System.out.println("用例\""+caseName+"\"性能提升,"+beforeDay+"平均值为"+beforeAverageValue+","+afterDay+"平均值为"+afterAverageValue);
                        increaseCaseCount++;
                        increaseCaseList.addAll(beforeList);
                        increaseCaseList.addAll(afterList);
                        insertResult(caseName,beforeDay, String.format("%.2f",beforeAverageValue),afterDay, String.format("%.2f",afterAverageValue),"false","性能提升",changeRange);
                    }
                    else if(unchanged==0){
                        System.out.println("用例\""+caseName+"\"性能不变");
                        unchangedCaseCount++;
                        list.addAll(beforeList);
                        list.addAll(afterList);
                        insertResult(caseName,beforeDay, String.format("%.2f",beforeAverageValue),afterDay, String.format("%.2f",afterAverageValue),"false","性能不变","");
                    }
                    else if(unchanged==1){
                        System.out.println("用例\""+caseName+"\"性能下降,"+beforeDay+" 平均值为"+beforeAverageValue+","+afterDay+" 平均值为"+afterAverageValue);
                        fallCaseCount++;
                        fallCaseList.addAll(beforeList);
                        fallCaseList.addAll(afterList);
                        insertResult(caseName,beforeDay, String.format("%.2f",beforeAverageValue),afterDay, String.format("%.2f",afterAverageValue),"false","性能下降",changeRange);
                    }
                }
            }
            String CSVFileName=CSVFile+afterDay+".csv";
            File file = new File(CSVFileName);
            if (file.exists()){
                FileUtils.delete(file);
            }
            writeToCsv(file, new String[]{"", "用例名", "运行时间", "TraceID", "TaskName", "运行时间", "引擎总时间","请求响应时间"}, list, fallCaseList, increaseCaseList, newList);

            WechatMessageUtils.sendFileToWeChat(file,key);
            WechatMessageUtils.sendMessageToWeChat("新增用例:"+newCaseCount+"   \n性能提升用例:"+increaseCaseCount+"   \n性能下降用例:"+fallCaseCount+"   \n性能未变化用例:"+unchangedCaseCount,key, "user");
        } catch (Exception e) {
            e.printStackTrace();
        }

    }

    //数据库处理
    private static void accessPolars(jsyPerformance jp) throws InterruptedException {
        try {
            System.out.println("jp.cases.size() = "+jp.cases.size());
            for (int i = 0; i < jp.cases.size(); i++) {
                System.out.println("https://work.jiushuyun.com/decision/zipkin/api/v2/trace/" + jp.cases.get(i).getTraceId());
                String url = "https://work.jiushuyun.com/decision/zipkin/api/v2/trace/" + jp.cases.get(i).getTraceId();
                String fineAuthToken = getFineAuthToken();
                String token = "tenantId=7ad5219f-8342-4a1c-b6d6-51ea2b6ea2b6; fine_remember_login=-1; fr_id_appname=jiushuyun; fine_auth_token=" + fineAuthToken;
                HttpUtils httpUtils = new HttpUtils(url, token);
                String response = httpUtils.connectAndGetRequest();
                if (response != null && response.equals("[]") ||
                        (httpUtils.getResponseCode() == 503) ||
                        (response != null && response.contains("503 Service Unavailable"))) {
                    i--;
                    continue;
                }
                JSONArray jsonArray = JSON.parseArray(response);

                for (int k = 0; k < jsonArray.size(); k++) {
                    JSONObject jsonObject = jsonArray.getJSONObject(k);
                    if (jsonObject.getString("tags") != null) {
                        JSONObject tags = jsonObject.getJSONObject("tags");
                        String taskName = tags.getString("taskName");
                        jp.cases.get(i).setTaskName(taskName);
                    }
                }

                for (String taskName : jp.cases.get(i).getTaskNames()) {

                    SimpleDateFormat formatter = new SimpleDateFormat("yyyy-MM-dd");
                    Date date = new Date(System.currentTimeMillis());
                    System.out.println("insert into jsyFormalEnvPerformance (用例名, traceid, taskName, curTime, response_time) " +
                            "values (\"" + jp.cases.get(i).getCaseName() + "\", \"" + jp.cases.get(i).getTraceId() + "\", \"" + taskName + "\" ,\"" + formatter.format(date) + "\", \"" + responseTimeMap.get(jp.cases.get(i).getTraceId()) + "\")");
                    DBUtils.updateData("insert into jsyFormalEnvPerformance (用例名, traceid, taskName, curTime, response_time) " +
                            "values (\"" + jp.cases.get(i).getCaseName() + "\", \"" + jp.cases.get(i).getTraceId() + "\", \"" + taskName + "\" ,\"" + formatter.format(date) + "\", \"" + responseTimeMap.get(jp.cases.get(i).getTraceId()) + "\")");

                    HttpUtils httpUtil = new HttpUtils("https://work.jiushuyun.com/decision/v1/polars/cluster/profile", token);
                    String sql = "{\"sql\":\" select * from TaskInfoTable where name='" + taskName + "'\"}";
                    System.out.println(sql);
                    String profileResponse = httpUtil.connectAndGetPostRequest(sql);
                    System.out.println(profileResponse);
                    if (profileResponse.split("\n").length == 2) {
                        String[] polarsData = profileResponse.split("\n")[1].split(" , ");

                        System.out.println("UPDATE jsyFormalEnvPerformance SET status=\"" + polarsData[1] + "\",type=\"" + polarsData[2] +
                                "\",create_time=\"" + polarsData[3] + "\",end_time=\"" + polarsData[4] +
                                "\",queue_time=\"" + polarsData[5] + "\",wait_resource_time=\"" + polarsData[6] +
                                "\",plan_time=\"" + polarsData[7] + "\",start_time=\"" + polarsData[8] +
                                "\",run_time=\"" + polarsData[9] + "\",finish_time=\"" + polarsData[10] +
                                "\",execution_all_time=\"" + polarsData[11] + "\",mem_peak=\"" + polarsData[12] +
                                "\",mem_current=\"" + polarsData[13] + "\",mem_capacity=\"" + polarsData[14] +
                                "\",pool_name=\"" + polarsData[15] + "\",work_node=\"" + polarsData[16] +
                                "\" where taskName=\"" + taskName + "\"");

                        DBUtils.updateData("UPDATE jsyFormalEnvPerformance SET status=\"" + polarsData[1] + "\",type=\"" + polarsData[2] +
                                "\",create_time=\"" + polarsData[3] + "\",end_time=\"" + polarsData[4] +
                                "\",queue_time=\"" + polarsData[5] + "\",wait_resource_time=\"" + polarsData[6] +
                                "\",plan_time=\"" + polarsData[7] + "\",start_time=\"" + polarsData[8] +
                                "\",run_time=\"" + polarsData[9] + "\",finish_time=\"" + polarsData[10] +
                                "\",execution_all_time=\"" + polarsData[11] + "\",mem_peak=\"" + polarsData[12] +
                                "\",mem_current=\"" + polarsData[13] + "\",mem_capacity=\"" + polarsData[14] +
                                "\",pool_name=\"" + polarsData[15] + "\",work_node=\"" + polarsData[16] +
                                "\" where taskName=\"" + taskName + "\"");
                    }
                }
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    /**
     * 拿token的*
     * @return token
     */
    private static String getFineAuthToken() {
   //     String fine_auth_token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxNzk0ZDlkOTk3MDA0NjkyYTMxMDJmYjI4NjdhMDVmMCIsInRlbmFudElkIjoiZDdjOWJhZGI5OTBjNDI3ZWE2MzAzYWYwY2UyMTI1ZjgiLCJpc3MiOiJmYW5ydWFuIiwiZGVzY3JpcHRpb24iOiJ5em05Mzk1MjIoMTc5NGQ5ZDk5NzAwNDY5MmEzMTAyZmIyODY3YTA1ZjApIiwiZXhwIjoxNjY5ODU5NzI3LCJpYXQiOjE2Njk2MDA1MjcsImp0aSI6ImI4ZDFnQ3dqZVJULzY5SG5VbEpKOTR3dko4ZmpySlphWWxDNUdCekNSR0VqdGJtZSJ9.ef7N5X9M62OCn44WDo0ccnO2sqmkCLrxbcEVa8P-16A";
        return JSYTokenUtils.getToken("15069244033","Maxnxl555!");
    }

    /**
     * 查询某一天耗时的集合*
     * @param time yyyy-MM-dd
     * @return 数据库中实体的列表
     */
    private static List<JsySqlPerformance> queryTime(String time){
        if (time==null || time.isEmpty()){
            return null;
        }
        List<JsySqlPerformance> result = new ArrayList<>();
        String sql = "SELECT `用例名` AS caseName,traceid AS traceId,GROUP_CONCAT(taskName SEPARATOR \";\") AS taskName,SUM(run_time) AS runTime,SUM(execution_all_time) AS executionAllTime,curTime AS curTime ,response_time as responseTime FROM `jsyFormalEnvPerformance` WHERE curTime = '"+time+"' GROUP BY traceid";
        System.out.println(sql);
        List<Map<String, String>> queries = DBUtils.query(sql, "caseName", "traceId", "taskName", "runTime", "executionAllTime", "curTime","responseTime");
        for (Map<String,String> map:queries){
            String caseName = map.get("caseName");
            String traceId = map.get("traceId");
            String taskNames = map.get("taskName");
            String runTime = map.get("runTime");
            String executionAllTime = map.get("executionAllTime");
            String curTime = map.get("curTime");
            String responseTime = map.get("responseTime");
            if (StringUtils.isNotEmpty(runTime)&&StringUtils.isNotEmpty(executionAllTime)){
                JsySqlPerformance performance = new JsySqlPerformance.Builder()
                        .setCaseName(caseName)
                        .setTraceId(traceId)
                        .setTaskNames(new ArrayList<>(Arrays.asList(StringUtils.split(taskNames, ";"))))
                        .setRunTime(Integer.parseInt(runTime))
                        .setExecutionAllTime(Integer.parseInt(executionAllTime))
                        .setCurTime(curTime)
                        .setResponseTime(responseTime==null?-1:Integer.parseInt(responseTime))
                                .build();

                result.add(performance);
            }
        }

        return result;
    }

    /**
     * 获得每个用例的最开始的时间*
     * @return 每个用例名以及最开始的时间
     */
    private static Map<String,String> queryEarlyTime(){
        Map<String,String> result = new HashMap<>();
        String sql = "SELECT `用例名` AS caseName,Min(curTime) as curTime FROM `jsyFormalEnvPerformance` GROUP BY `用例名`";
        List<Map<String, String>> query = DBUtils.query(sql,"caseName","curTime");
        for (Map<String,String> map : query){
            result.put(map.get("caseName"),map.get("curTime"));
        }
        return result;

    }


    /**
     * 判断性能的*
     * @param beforeAverageValue 基准平均值
     * @param afterAverageValue 现在的平均值
     * @param range 波动范围，例如0.2就是允许80-120
     * @return 数字枚举代表性能波动
     */
    private static int isUnchanged(double beforeAverageValue,double afterAverageValue,double range){
        double max = beforeAverageValue * (1+range);
        double min = beforeAverageValue * (1-range);
        System.out.println("afterAverageValue="+afterAverageValue);
        System.out.println("beforeAverageValue="+beforeAverageValue);
        if ((afterAverageValue<=max)&&(afterAverageValue>=min)){
            return 0;
        }else if(afterAverageValue>max) {
            return 1;
        }else{
            return -1;
        }
    }

    /**
     * 获得某个用例的平均值*
     * @param list 用例多次执行出的列表
     * @return 平均值
     */
    private static double getAverageValue(List<JsySqlPerformance> list){
        double result=0,number=0;
        if (list==null||list.isEmpty()){
            return -1;
        }
        for (JsySqlPerformance performance:list){
            result+=performance.getRunTime();
            number+=1;
        }
        if (number==0){
            return -1;
        }else {
            return result/number;
        }
    }

    /**
     * 将所有数据按照用例区分，方便后面处理*
     * @param list 所有用例的所有数据
     * @return 一个map，键是用例名，值是用例对应的所有用例的列表
     */
    private static Map<String,List<JsySqlPerformance>> groupList(List<JsySqlPerformance> list){
        Map<String,List<JsySqlPerformance>> result = new HashMap<>();
        if (list==null||list.isEmpty()){
            return null;
        }
        for (JsySqlPerformance performance:list){
            if (result.containsKey(performance.getCaseName())){
                List<JsySqlPerformance> list1 = result.get(performance.getCaseName());
                list1.add(performance);
            }
            else {
                List<JsySqlPerformance> list1 = new ArrayList<>();
                list1.add(performance);
                result.put(performance.getCaseName(),list1);
            }
        }
        return result;
    }

    /**
     * 删除某天中数据库中数据，主要是为了防止当天前一次的数据对这次产生影响*
     * @param afterDay string类型时间
     * @return 是否删除成功
     */
    private static int deleteAfterDayData(String afterDay){
        String sql = "delete from jsyFormalEnvPerformance where curTime='"+afterDay+"'";
        return DBUtils.updateData(sql);
    }


    /**
     * 向结果表中添加数据*
     * @param caseName 用例名
     * @param standardTime 基准日期
     * @param standardRunTime 基准运行时间
     * @param currentTime 当前日期
     * @param currentRunTime 本次运行时间
     * @param isNew 是否为新增用例
     * @param changeDirection 是否有性能波动
     * @param changeRange 波动范围
     */
    private static void insertResult(String caseName,String standardTime,String standardRunTime,String currentTime,String currentRunTime,String isNew,String changeDirection,String changeRange){
        String id = caseName+"_"+currentTime;
        String sql = "insert into jsyFormalEnvPerformanceResult (id,caseName,standardTime,standardRunTime,currentTime,currentRunTime,isNew,changeDirection,changeRange) VALUES " +
                "(\""+id+"\",\""+caseName+"\",\""+standardTime+"\",\""+standardRunTime+"\",\""+currentTime+"\",\""+currentRunTime+"\",\""+isNew+"\",\""+changeDirection+"\",\""+changeRange+"\")";
        DBUtils.updateData(sql);
    }

    /**
     * 删除insertResult中插入的数据，也是为了防止一天跑多次的情况*
     * @return 是否删除成功
     */
    private static int deleteLastDayResultData(){
        String sql = "delete from jsyFormalEnvPerformanceResult where currentTime=\""+afterDay+"\";";
        return DBUtils.updateData(sql);
    }





    /**
     * 写csv文件*
     * @param file csv文件
     * @param names 列名
     * @param list 性能不变列表
     * @param fallList 性能上升列表
     * @param increaseList 性能下降列表
     * @param newList 新增列表
     */
    private static void writeToCsv(File file,String[] names,List<JsySqlPerformance> list,List<JsySqlPerformance> fallList,List<JsySqlPerformance> increaseList,List<JsySqlPerformance> newList){
        if (!file.exists()){
            try {
                boolean newFile = file.createNewFile();
                System.out.println(newFile);
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
        try {
            CSVWriter writer = new CSVWriter(new OutputStreamWriter(new FileOutputStream(file),"GBK"),CSVWriter.DEFAULT_SEPARATOR,CSVWriter.NO_QUOTE_CHARACTER);
            writer.writeNext(names);

            if (newList!=null&&newList.size()>0){
                writeLines(writer,newList,"新增用例");
            }
            if (fallList!=null&&fallList.size()>0){
                writeLines(writer,fallList,"性能下降");
            }
            if (increaseList!=null&&increaseList.size()>0){
                writeLines(writer,increaseList,"性能上升");
            }
            if (list!=null&&list.size()>0){
                writeLines(writer,list,"性能不变");
            }

            writer.flush();
            writer.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    private static void writeLines(CSVWriter writer,List<JsySqlPerformance> list,String description){
        String name = "";
        int i=0;
        if (list!=null&&list.size()>0){
            for (JsySqlPerformance performance:list){
                i++;
                if ((!name.equals(performance.getCaseName()))&&(!"新增用例".equals(description))){
                    writer.writeNext(new String[]{});
                    name= performance.getCaseName();
                }
                System.out.println("开始写文件");
                if (i==1){
                    writer.writeNext(new String[]{description,performance.getCaseName(),performance.getCurTime(),performance.getTraceId(),StringUtils.join(performance.getTaskNames(),";"), String.valueOf(performance.getRunTime()), String.valueOf(performance.getExecutionAllTime()),String.valueOf(performance.getResponseTime())});
                }
                else {
                    writer.writeNext(new String[]{"",performance.getCaseName(),performance.getCurTime(),performance.getTraceId(),StringUtils.join(performance.getTaskNames(),";"), String.valueOf(performance.getRunTime()), String.valueOf(performance.getExecutionAllTime()),String.valueOf(performance.getResponseTime())});
                }
             }
        }
        else {
            System.out.println("没数据！");
        }

    }


}