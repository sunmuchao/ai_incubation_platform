package ci.benchMark;

import base.db.JSYDBUtils;
import ci.UnitTestEngine.UnitTestTaskInformation;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.List;
import java.util.Map;

/**
 * @author sunmuchao
 * @date 2023/10/12 11:25 上午
 */
public class UnitTestTaskManager {
    private UnitTestTaskInformation utti;

    public UnitTestTaskManager(UnitTestTaskInformation utti){
        this.utti = utti;
    }


    //结果更新数据库
    //判断是否当前uuid的所有任务均执行完成
    public void manage() throws Exception {
        String sql = "UPDATE CI_Schedul_Information \n" +
                "SET isFinish = true \n" +
                "WHERE uuid = '" + utti.getUuid() + "' AND sonJobName = '" + utti.getOperatorNodeNames().get(0) + "' AND number = " + utti.getDocumentNumber() + ";";
        if(JSYDBUtils.updateData(sql) == 0) {
            throw new Exception("修改CI_Schedul_Information表信息失败");
        }


        //判断是否当前uuid的所有任务均执行完成
        String query = "select count(*) as count from CI_Schedul_Information where uuid=\"" + utti.getUuid() + "\" and isFinish=false;";
        List<Map<String, String>> result = JSYDBUtils.query(query, "count");
        int count = Integer.parseInt(result.get(0).get("count"));
        /*if(count == 0){
            //如果所有任务均执行完成，则触发CIReduse发送结果
            String jobName = "CIReduse11";
            utti.generateTomlFile("");
            String cmd = "python3 " + workPath + "/jenkinsTool/jenkins_buildReduse.py " + jobName + " " + uuid + " " + builder + " " + prId + " " + branch + " " + isContainBIChange + " " + isContainHihidataChange;
            System.out.println(cmd);
            Process proc = Runtime.getRuntime().exec(cmd);
            proc.waitFor();
            String err = readOutput(proc.getErrorStream());
            if (err != null && !err.equals("")) throw new Exception("触发operator执行失败的错误信息:" + err);
        }else{
            System.out.println("还有" + count + "个sonjob没有执行完成");
        }*/
    }


    private static String readOutput(InputStream inputStream) throws IOException {
        StringBuffer outputLines = new StringBuffer();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream))) {
            String line;
            while ((line = reader.readLine()) != null) {
                outputLines.append(line + "\n");
            }
        }
        return outputLines.toString();
    }
}
