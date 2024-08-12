package profile;

import base.db.DBUtils;
import base.http.HttpUtils;
import base.third.jsy.JSYTokenUtils;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONPath;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.common.base.Joiner;
import com.google.common.collect.ImmutableList;
import org.apache.commons.io.FileUtils;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpPost;
import org.apache.http.entity.ContentType;
import org.apache.http.entity.StringEntity;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.util.EntityUtils;
import polarsPerformance.PolarsAccessor;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.sql.SQLException;
import java.text.MessageFormat;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class SlowQueryMonitor {

    static String token = getFineAuthToken();
    static String cookie = "tenantId=7ad5219f-8342-4a1c-b6d6-51ea2b6ea2b6; fine_remember_login=-1; fr_id_appname=jiushuyun; fine_auth_token="+ token;
    //超时时间，单位为s
    final static int timeout = Integer.parseInt(Optional.ofNullable(System.getProperty("slow_query.checkout_time")).orElse("60").trim());
    //每过多长时间检查一次，单位为min
    final static int checkoutTime = Integer.parseInt(Optional.ofNullable(System.getProperty("slow_query.checkout_time")).orElse("10").trim());

    //多长时间内出现的算是重复单位为min
    final static int repeatTime = Integer.parseInt(Optional.ofNullable(System.getProperty("slow_query.repeat_time")).orElse("180").trim());

    static String lastStopTime = null;
    final static String webhook = Optional.ofNullable((System.getProperty("slow_query.webhook"))).orElse("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=2f745e39-a2b8-4d95-b624-09518a5344ab");

    public static void main(String[] args) throws InterruptedException, SQLException {


        final ScheduledExecutorService service = Executors.newScheduledThreadPool(2);
        service.scheduleWithFixedDelay(()->{
            try {
                token = getFineAuthToken();
                cookie = "tenantId=7ad5219f-8342-4a1c-b6d6-51ea2b6ea2b6; fine_remember_login=-1; fr_id_appname=jiushuyun; fine_auth_token="+ token;
                String stopTime = getTime(new Date());
                String mStartTime = lastStopTime==null ? getBeforeTime(stopTime,checkoutTime):lastStopTime;
                lastStopTime=stopTime;
                List<Map<String, String>> list = slowQueryMap(mStartTime, stopTime);
                if (list==null || list.isEmpty()){
                    System.out.println("无超时的profile");
                    return;
                }
                List<String> taskNames = new ArrayList<>();
                for (Map<String,String> map:list){
                    String taskName = map.get("taskName");
                    int runTime = Integer.parseInt(map.get("runTime"));
                    int startTime = Integer.parseInt(map.get("startTime"));
                    int sumTime = Integer.parseInt(map.get("sumTime"));
                    int queueTime = Integer.parseInt(map.get("queueTime"));
                    Map<String, String> tableNameAndUserName = getTableNameAndUserName(taskName);
                    System.out.println(taskName+"超时,其中,总时间="+sumTime+",queueTime="+queueTime+",startTime="+startTime+",真实运行时间runTime="+runTime);
                    if (sumTime-queueTime-startTime<=timeout*1000){
                        String txt = taskName+"排队超时,其中,总时间="+sumTime+",queueTime="+queueTime+",startTime="+startTime+",真实运行时间runTime="+runTime+",因此不会被记录";
                        taskNames.add(txt);
                        FileUtils.writeStringToFile(new File("/opt/nxl/test.txt"),txt, StandardCharsets.UTF_8,true);
                        continue;
                    }
                    if (tableNameAndUserName.isEmpty()){
                        String message = taskName+"超时但获取用户名和表名失败!";
                        taskNames.add(message);
                        FileUtils.writeStringToFile(new File("/opt/nxl/test.txt"),message, StandardCharsets.UTF_8,true);
                        continue;
                    }
                    String tableName = tableNameAndUserName.get("tableName");
                    String userName = tableNameAndUserName.get("userName");
                    if(tableName==null || userName==null){
                        taskNames.add(taskName);
                        continue;
                    }
                    int numbers = getNumbers(userName, tableName, stopTime);
                    System.out.println("numbers = " + numbers);
                    if (numbers==0){
                        String insertSql = "insert into slowQueryTable (taskName,runTime,tableName,userName,time,isShow) values (\"" + taskName + "\",\"" + runTime + "\",\"" + tableName + "\",\"" + userName + "\",\"" + stopTime + "\",\"" + "true" + "\");";
                        System.out.println(insertSql);
                        DBUtils.updateData(insertSql);
                        String txt="当前时间为"+getTime(new Date())+" : taskName = "+taskName+"超时且已经被记录和发到企微 \n";
                        FileUtils.writeStringToFile(new File("/opt/nxl/test.txt"),txt, StandardCharsets.UTF_8,true);
                        taskNames.add(taskName);
                    }
                    else {
                        String insertSql = "insert into slowQueryTable (taskName,runTime,tableName,userName,time,isShow) values (\"" + taskName + "\",\"" + runTime + "\",\"" + tableName + "\",\"" + userName + "\",\"" + stopTime + "\",\"" + "false" + "\");";
                        DBUtils.updateData(insertSql);
                        taskNames.add(taskName+":重复"+numbers+"次");
                        String txt="当前时间为"+getTime(new Date())+" : taskName = "+taskName+"超时且已经被记录但是没有发到企微，因为已经有同类型的超时"+numbers+"次 \n";
                        FileUtils.writeStringToFile(new File("/opt/nxl/test.txt"),txt,StandardCharsets.UTF_8,true);
                    }
                }
                sentTimeOutMessage(taskNames);

            }
            catch (Exception e){
                e.printStackTrace();
            }

        },0, checkoutTime, TimeUnit.MINUTES);



    }

    private static String getFineAuthToken() {

        //     String fine_auth_token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxNzk0ZDlkOTk3MDA0NjkyYTMxMDJmYjI4NjdhMDVmMCIsInRlbmFudElkIjoiZDdjOWJhZGI5OTBjNDI3ZWE2MzAzYWYwY2UyMTI1ZjgiLCJpc3MiOiJmYW5ydWFuIiwiZGVzY3JpcHRpb24iOiJ5em05Mzk1MjIoMTc5NGQ5ZDk5NzAwNDY5MmEzMTAyZmIyODY3YTA1ZjApIiwiZXhwIjoxNjY5ODU5NzI3LCJpYXQiOjE2Njk2MDA1MjcsImp0aSI6ImI4ZDFnQ3dqZVJULzY5SG5VbEpKOTR3dko4ZmpySlphWWxDNUdCekNSR0VqdGJtZSJ9.ef7N5X9M62OCn44WDo0ccnO2sqmkCLrxbcEVa8P-16A";
        return JSYTokenUtils.getToken("15505286929","Yzp145632");
    }

    /**
     * *查询profile
     * @param startTime 开始时间
     * @param stopTime 结束时间
     * @return 时间大于60s的profile的taskName和一些别的参数
     */
    private static List<Map<String,String>> slowQueryMap(String startTime, String stopTime){
        List<Map<String,String>> result = new ArrayList<>();
        String url = "https://work.jiushuyun.com/decision/v1/polars/cluster/profile";
        String sql = "select * from TaskInfoTable where type='QUERY' and execution_all_time>"+(timeout*1000)+" and end_time between '"+startTime+"' and '"+stopTime+"' order by run_time desc";
        String param = "{\"sql\":\"" + sql + "\"}";

        HttpUtils httpUtils = new HttpUtils(url,cookie);
        System.out.println("查询语句 :" + param);
        String response = httpUtils.connectAndGetPostRequest(param);
        String[] rowData = response.split("\n"),label = response.split("\n")[0].split(" , ");
        int taskNameIndex=-1,runTimeIndex=-1,startTimeIndex=-1,sumTimeIndex=-1,queueTimeIndex=-1;
        for (int i=0;i<label.length;i++){
            if ("name".equals(label[i])){
                taskNameIndex=i;
            }
            else if ("run_time".equals(label[i])){
                runTimeIndex=i;
            }
            else if ("start_time".equals(label[i])){
                startTimeIndex=i;
            }
            else if("execution_all_time".equals(label[i])){
                sumTimeIndex=i;
            }
            else if("queue_time".equals(label[i])){
                queueTimeIndex=i;
            }
        }
        if (taskNameIndex<0 || runTimeIndex<0){return null;}
        for (int i=1;i<rowData.length;i++){
            String[] data = rowData[i].split(" , ");
            Map<String,String> map = new HashMap<>();
            map.put("taskName",data[taskNameIndex]);
            map.put("runTime",data[runTimeIndex]);
            map.put("startTime",data[startTimeIndex]);
            map.put("sumTime",data[sumTimeIndex]);
            map.put("queueTime",data[queueTimeIndex]);
            System.out.println("taskName = " + data[taskNameIndex]);
            result.add(map);
        }

        return result;
    }


    /**
     * *
     * @param taskName 要查询数据的taskName
     * @return Map中包含了表名和用户名
     */
    private static Map<String,String> getTableNameAndUserName(String taskName){
        StringBuilder url = new StringBuilder("https://work.jiushuyun.com/decision/zipkin/api/v2/traces?annotationQuery=taskName%3D").append(taskName).append("&limit=10&lookback=10800000");
        System.out.println(url);
        Map<String,String> result = new HashMap<>();
        HttpUtils httpUtils = new HttpUtils(url.toString(),cookie);
        List<String> tableNameList=null,userNameList=null;
        int numbers=0;
        while(numbers<5){
            try {
                String s = httpUtils.connectAndGetRequest();
                JSONArray jsonArray = JSONArray.parseArray(s);
                tableNameList = (List<String>) JSONPath.eval(jsonArray,"$..tableId");
                userNameList = (List<String>) JSONPath.eval(jsonArray,"$..remoteEndpoint.ipv4");
                if (userNameList == null || userNameList.isEmpty()){
                    System.out.println("更新超时！！！");
                    userNameList = (List<String>) JSONPath.eval(jsonArray,"$..userId");
                }
                break;
            } catch (Exception e) {
                numbers+=1;
                try {
                    Thread.sleep(30*1000);
                } catch (InterruptedException ex) {
                    ex.printStackTrace();
                }
                e.printStackTrace();
            }
        }

        if ((tableNameList == null || tableNameList.isEmpty()) || (userNameList == null || userNameList.isEmpty())){
            return result;
        }
        System.out.println("tableName="+tableNameList.get(0)+",userName="+userNameList.get(0).split(":")[0]);
        result.put("tableName",tableNameList.get(0));
        result.put("userName",userNameList.get(0).split(":")[0]);
        return result;
    }


    /**
     * 查看在限定时间内是否有重复超时任务*
     * @param userName 操作的用户
     * @param tableName 操作的表名
     * @param stopTime 会以这个时间为终点，向前查找repeatTime分钟内的重复事件
     * @return 重复事件的数量（一般来说是1）
     */
    private static int getNumbers(String userName,String tableName,String stopTime){
        String selectSql = "select * from slowQueryTable where isShow='true' and userName='" + userName + "' and tableName='"+tableName+"' and time between '"+getBeforeTime(stopTime,repeatTime)+"' and '"+stopTime+"'";
        System.out.println("selectSql:"+selectSql);
        List<Map<String, String>> query = DBUtils.query(selectSql, "userName", "tableName");
        if (query.isEmpty()){
            return 0;
        }


        String selectSql2 = "select * from slowQueryTable where userName='" + userName + "' and tableName='"+tableName+"' and time between '"+getBeforeTime(stopTime,repeatTime)+"' and '"+stopTime+"'";
        System.out.println("selectSql2:"+selectSql2);
        List<Map<String, String>> query1 = DBUtils.query(selectSql2, "userName", "tableName");
        return query1.size();
    }

    /**
     * 获得对应时间前hours小时的标准格式时间
     * @param time 时间
     * @param minutes 需要往前移动多少分钟
     * @return 标准格式时间
     */
    private static String getBeforeTime(String time,int minutes){
        SimpleDateFormat simpleDateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        Date date = null;
        try {
            date = simpleDateFormat.parse(time);
        } catch (ParseException e) {
            e.printStackTrace();
        }
        if (date == null){return null;}
        Calendar calendar = Calendar.getInstance();
        calendar.setTime(date);
        calendar.set(Calendar.MINUTE,calendar.get(Calendar.MINUTE)-minutes);
        return simpleDateFormat.format(calendar.getTime());
    }


    /**
     * 日期转换*
     * @param date 日期
     * @return yyyy-MM-dd HH:mm:ss格式
     */
    private static String getTime(Date date){
        SimpleDateFormat simpleDateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        return simpleDateFormat.format(date);
    }

    private static void sentTimeOutMessage(List<String> taskNames) throws Exception {
        if (taskNames.isEmpty())return;
        Map<String, Object> parameter = new HashMap<>(2, 1);
        Map<String, Object> text = new HashMap<>(2, 1);
        text.put("content", MessageFormat.format("最近{0}s内耗时超过{1}s的任务\n{2}",checkoutTime*60 ,timeout , Joiner.on("\n").join(taskNames)));
        text.put("mentioned_list", ImmutableList.of());
        parameter.put("msgtype", "text");
        parameter.put("text", text);
        sendWeChatMessage(parameter, "Failed Tasks : " + taskNames);

    }

    /**
     * @param parameter 要发送的信息
     * @param message   发送失败后，打印到控制台的信息
     * @throws Exception Exception
     */
    private static void sendWeChatMessage(Map<String, Object> parameter, String message) throws Exception {
        HttpPost httpPost = new HttpPost(webhook);
        httpPost.setEntity(new StringEntity(new ObjectMapper().writeValueAsString(parameter), ContentType.APPLICATION_JSON));
        try (CloseableHttpResponse resp = HttpClients.createDefault().execute(httpPost)) {
            System.out.println(EntityUtils.toString(resp.getEntity()));
            System.out.println(message);
        }
    }


}
