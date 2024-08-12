package ci.benchMarkCluster;

import base.config.Application;
import base.http.JSchUtil;
import org.apache.commons.lang3.StringUtils;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class InitializeData {

    private static final String rootPath = "/opt/nxl/cluster_test/";
    private static JSchUtil jSchUtil;
    static {
        jSchUtil = Application.getPolarsClusterSessionInstance();
    }

    private static List<String> getFileList(){
        List<String> execList = jSchUtil.execQueryList("cd " + rootPath + "suite; ls");
        StringBuilder files = new StringBuilder();
        for (String s:execList){
            files.append(s).append(" ");
        }
        return new ArrayList<>(Arrays.asList(files.toString().split(" ")));
    }



    public static void main(String[] args) {
        if (jSchUtil==null) return;
        try{
            List<String> fileList = getFileList();
            String cdRoot = "cd "+rootPath+";";
            for (String file:fileList){
                //判断是否已经执行过导入
                if (StringUtils.isNotEmpty(jSchUtil.execQuery("cat "+rootPath+"workerSpace/pls/"+file.replace("suite2","pls")))){
                    System.out.println(file+"之前已经导入，无需执行");
                    continue;
                }
                //准备数据
                System.out.print("准备数据:");
                jSchUtil.execQuery(cdRoot+"cp ./suite/"+file+" ./suite_runtime;unzip -d ./suite_runtime/ ./suite_runtime/"+file);

                //替换pls文件中的ver
                System.out.println("替换pls的ver:");
                List<String> verList = jSchUtil.execQueryList(cdRoot+"cat ./suite_runtime/query.pls | grep '\"ver\"'");
                if (!verList.isEmpty()){
                    for (String ver:verList){
                        System.out.println(ver);
                        System.out.println(jSchUtil.execQuery(cdRoot+"sed -i 's/"+ StringUtils.trim(ver) +"/\"ver\": 0/g'" + " ./suite_runtime/query.pls"));
                    }
                }

                //执行数据导入
                System.out.print("数据导入:");
                jSchUtil.execQuery(cdRoot+"./jdk11/bin/java -DloadClass=com.fanruan.polars.hihidata.register.HihidataModuleRegister " +
                        "-Dtype=hihidataimp  -DtableSpace=default_ts -Dpath=./suite_runtime/"+file+" -DclusterIp=192.168.5.241 " +
                        "-DclusterPort=8000 -cp polars-assembly-1.0-SNAPSHOT.jar com.fanruan.polars.shell.SunFlow2Cluster");

                //保存pls文件
                System.out.print("保存文件:");
                jSchUtil.execQuery(cdRoot+"mv ./suite_runtime/query.pls ./workerSpace/pls/"+ file.replace("suite2","pls"));
                //删除工作目录，为下一次做准备
                System.out.print("删除工作目录:");
                jSchUtil.execQuery(cdRoot+"rm -rf ./suite_runtime/*");
            }
        }catch (Exception e){
            e.printStackTrace();
        }finally {
            jSchUtil.closeSession();
        }
    }
}
