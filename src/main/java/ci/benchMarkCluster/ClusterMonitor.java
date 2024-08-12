package ci.benchMarkCluster;

import base.config.Application;
import base.db.DBUtils;
import base.http.JSchUtil;
import base.third.wechat.WechatMessageUtils;
import com.google.common.base.Preconditions;
import org.apache.commons.lang3.StringUtils;

import java.sql.Timestamp;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class ClusterMonitor {

    private static final boolean repeatPolicy = Boolean.parseBoolean(System.getProperty("repeatPolicy"));
    private static String basePath = "";
    private static final JSchUtil polarsClusterSessionInstance = Application.getPolarsClusterSessionInstance();
    private static final JSchUtil clusterSession = Application.getClusterSessionInstance();
    private static Map<String,Cluster> baseClusters = new HashMap<>();
    private static Map<String,Cluster> clusters = new HashMap<>();
    private static final String key = Optional.ofNullable((System.getProperty("webhook"))).orElse("3a0c7517-9ce6-48fc-8ded-f4b4ea546c03");
    private static int isRepeat = 0;
    private static double lastCrashTimeStamp = System.currentTimeMillis();
    private static boolean needToReportChange = true;

    private static void updateCluster(){
        Iterator<String> iterator = clusters.keySet().iterator();
        boolean needUpdate = false;
        while(iterator.hasNext()){
            String id = iterator.next();
            if (baseClusters.isEmpty()||!baseClusters.containsKey(id)) {
                needUpdate=true;
                break;
            }
        }
        if (needUpdate){
            StringBuilder message = new StringBuilder("cluster nodes have been updated").append("\nbefore:")
                    .append(ergodicMap(baseClusters)).append("\nafter:").append(ergodicMap(clusters));
            System.out.println("need to update tables");
            DBUtils.updateData("delete from cluster_initial;");
            StringBuilder sql = new StringBuilder("INSERT INTO cluster_initial (`name`,`id`) VALUES ");
            baseClusters=clusters;

            for (Map.Entry<String, Cluster> next : baseClusters.entrySet()) {
                sql.append("('").append(next.getValue().getName()).append("','").append(next.getValue().getId()).append("'),");
            }
            sql.deleteCharAt(sql.length()-1).append(";");
            int i = DBUtils.updateData(sql.toString());
            if (i==0){
                System.out.println("update cluster table failed!!");
            }else {
                if (needToReportChange){
                    WechatMessageUtils.sendMessageToWeChat(message.toString(),key,"user");
                    //插入数据库
                    String insertSql = "INSERT INTO cluster_state (`timeStamp`,`state`,`state_before`,`state_after`) VALUES (\""+ new Timestamp(System.currentTimeMillis()) +"\",\"update\",\""+ergodicMap(baseClusters)+"\",\""+ergodicMap(clusters)+"\")";
                    if (DBUtils.updateData(insertSql)>0){
                        System.out.println("插入成功");
                    }else {
                        System.out.println("插入失败");
                    }
                }
            }
        }else {
            System.out.println("no need to update tables");
        }

        SimpleDateFormat formatter= new SimpleDateFormat("yyyy-MM-dd  HH:mm:ss");
        Date date = new Date(System.currentTimeMillis());
        System.out.println("当前时间为"+formatter.format(date)+",线程结束!");

    }

    private static void checkClusterState(){
        Iterator<String> iterator = baseClusters.keySet().iterator();
        List<Cluster> deadNode = new ArrayList<>();
        while (iterator.hasNext()){
            String next = iterator.next();
            if (!clusters.containsKey(next)) {
                deadNode.add(baseClusters.get(next));
            }
        }
        for (Map.Entry<String, Cluster> next : clusters.entrySet()) {
            if (!next.getValue().getState()) deadNode.add(clusters.get(next.getKey()));
        }

        if (deadNode.isEmpty()){
            System.out.println("it has no dead node");
            isRepeat=0;
        }else {
            if (!repeatPolicy || isRepeat == 0){
                String diff = "";
                if (Objects.nonNull(clusterSession)){
                    diff = clusterSession.execQuery("diff /opt/nxl/cluster_update /opt/nxl/cluster_last_update");
                }
                if (StringUtils.isNotEmpty(diff)){
                    System.out.println("cluster update jar");
                    if (Objects.nonNull(clusterSession)){
                        clusterSession.execQuery("/bin/cp -r /opt/nxl/cluster_update /opt/nxl/cluster_last_update");
                    }
                }else {
                    System.out.println("it has dead nodes");
                    StringBuilder message = new StringBuilder("some nodes in cluster crash! \nthere are dead nodes: \n");
                    for (Cluster cluster :deadNode){
                        message.append(cluster.getId()).append(" : ").append(cluster.getName()).append("\n");
                    }
                    message.deleteCharAt(message.length()-1);

                    WechatMessageUtils.sendMessageToWeChat(message.toString(),key, "user");

                    //存入数据库
                    String insertSql = "INSERT INTO cluster_state (`timeStamp`,`state`,`state_before`,`state_after`) VALUES (\""+ new Timestamp(System.currentTimeMillis()) +"\",\"crash\",\""+ergodicMap(baseClusters)+"\",\""+ergodicMap(clusters)+"\")";
                    if (DBUtils.updateData(insertSql)>0){
                        System.out.println("插入成功");
                    }else {
                        System.out.println("插入失败");
                    }
                    //如果5分钟内连续宕机则不会连续报警宕机和重启信息
//                    if (System.currentTimeMillis()-lastCrashTimeStamp>5*60*1000){
//                        lastCrashTimeStamp=System.currentTimeMillis();
//                        needToReportChange=true;
//                        WechatMessageUtils.sendMessageToWeChat(message.toString(),key);
//                    }else {
//                        lastCrashTimeStamp=System.currentTimeMillis();
//                        needToReportChange=false;
//                    }
                }
            }else {
                System.out.println("it has dead nodes but not to report");
            }
            isRepeat++;
        }

    }

    private static void getBaseCluster(){
        SimpleDateFormat formatter= new SimpleDateFormat("yyyy-MM-dd  HH:mm:ss");
        Date date = new Date(System.currentTimeMillis());
        System.out.println("当前时间为"+formatter.format(date)+",新线程开始!");
        List<Map<String, String>> query = DBUtils.query("SELECT * from cluster_initial", "name", "id");
        if (query.isEmpty()) return;
        for (Map<String, String> map : query){
            Cluster cluster = new Cluster(map.get("name"),true,map.get("id"));
            baseClusters.put(cluster.getId(),cluster);
        }
    }

    private static void getClusterState(){
        clusters = new HashMap<>();
        if (polarsClusterSessionInstance != null) {
            String getClusterStateString = polarsClusterSessionInstance.execQuery("cd " + basePath + "/monitor && ../jdk11/bin/java com.nxl.utils.NodeStateUtils ../monitor.txt && echo 'get cluster state successfully';");
            if (!getClusterStateString.contains("get cluster state successfully")){
                System.out.println("get cluster state error!");
                System.out.println(getClusterStateString);
 //               LOGGER.error("get cluster state error!");
                return;
            }
            List<String> list = polarsClusterSessionInstance.execQueryList("cd " + basePath + " && cat monitor.txt;");
            if (list == null || list.size()==0 || list.size()%3!=0){
                System.out.println("no monitor.txt!");
  //              LOGGER.error("get cluster state error!");
                return;
            }else {
                System.out.println("cluster states:");
                System.out.println(Arrays.toString(list.toArray()));
            }
            for (int i = 0;i<list.size();i+=3){
                Cluster cluster = new Cluster(list.get(i), StringUtils.equals("Running",list.get(i+1)),list.get(i+2));
                clusters.put(cluster.getId(),cluster);
            }
        }else {
            System.out.println("get session error!");
   //         LOGGER.error("get session error!");
        }
    }

    private static String ergodicMap(Map<String,Cluster> map){
        StringBuilder result = new StringBuilder();
        for (Map.Entry<String, Cluster> next : map.entrySet()) {
            result.append(next.getValue().toString());
        }
        return result.toString();
    }

    public static void main(String[] args) {
        System.out.println("repeatPolicy is "+repeatPolicy);
        Preconditions.checkArgument(args!=null && args.length==1, "至少需要一个参数！");
        System.out.println("key = " + key);
        //monitor所在目录
        basePath=args[0];
        Runnable runnable = () -> {
            System.out.println(" ");
            getBaseCluster();
            getClusterState();
            checkClusterState();
            updateCluster();
            System.out.println(" ");
        };
        ScheduledExecutorService scheduledExecutorService= Executors.newSingleThreadScheduledExecutor();
        scheduledExecutorService.scheduleAtFixedRate(runnable, 0, 10, TimeUnit.SECONDS);
    }
}
