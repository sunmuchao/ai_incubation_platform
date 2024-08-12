package base.config;

import base.http.JSchUtil;
import buriedPoint.DBUtils;
import base.file.RemoteFileUtils;
import com.jcraft.jsch.JSchException;

public class Application {
    public static RemoteFileUtils fileUtils;
    public static DBUtils dbUtils;
    public static String suitePath;
    public static String jsyCookie;
    public static String fine_auth_token;
    public static String workPath;

    //埋点处理开关
    public static Boolean buriedPointSwitch = true;
    //jira推送bug开关
    public static Boolean jiraSwitch = true;
    //上一版本发布时间,格式：yyyy-MM-dd
    public static String publishedLastVersionDate = "2022-11-22";

    public static RemoteFileUtils getRemoteFileUtilsInstance() throws Exception {
        if(fileUtils == null){
            fileUtils = new RemoteFileUtils("192.168.5.94",22,"root","polars","/data/smc/metric");
        }
        return fileUtils;
    }

    public static DBUtils getDBUtilsInstance() {
        if(dbUtils == null){
            dbUtils = new DBUtils();
            dbUtils.setConnection("jdbc:mysql://47.102.211.0:3306/bi_performance_auto?user=fanruan&password=Fanruan&useUnicode=true&characterEncoding=utf8&autoReconnect=true&useSSL=false");

        }
        return dbUtils;
    }
    public static JSchUtil getPolarsClusterSessionInstance(){
        try {
            JSchUtil jSchUtil = new JSchUtil();
            jSchUtil.initializeSession("root", "192.168.5.22", "polars");
            return jSchUtil;
        } catch (JSchException e) {
            System.out.println(e+"程序退出!");
            return null;
        }
    }

    public static JSchUtil getClusterSessionInstance(){
        try {
            JSchUtil jSchUtil = new JSchUtil();
            jSchUtil.initializeSession("root","192.168.5.241","ilovejava1!");
            return jSchUtil;
        } catch (JSchException e) {
            System.out.println(e+"程序退出!");
            return null;
        }
    }

    public static JSchUtil getBIJenkinsSessionInstance(){
        try {
            JSchUtil jSchUtil = new JSchUtil();
            jSchUtil.initializeSession("root", "192.168.5.10", "Yunzx@123");
            return jSchUtil;
        } catch (JSchException e) {
            System.out.println(e+"程序退出!");
            return null;
        }
    }

    public static void setSuitePath(String suitePath1) {
        suitePath = suitePath1;
    }

    public static void setJsyCookie(String jsyCookie1) {
        jsyCookie = jsyCookie1;
        fine_auth_token = jsyCookie1.split("fine_auth_token=")[1].split(";")[0];
    }

    public static void setWorkPath(String workPath1) {
        workPath = workPath1;
    }
}

