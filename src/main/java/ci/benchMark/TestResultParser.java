package ci.benchMark;

import base.db.JSYDBUtils;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.HashMap;
import java.util.Map;

/**
 * @author sunmuchao
 * @date 2023/10/8 2:36 下午
 */
public class TestResultParser {
    public static void main(String[] args) {
        String uuid = args[0];
        String executePath = args[1];
        try {
            Process proc = null;
            String cmd = "find " + executePath + " -type f -path \"*/target/surefire-reports/*.xml\" -exec grep -H \"<testcase\" {} \\; | awk -F'[= \"]' '{print \"classname: \" $10 \", name: \" $6 \", time: \" $(NF-1)}' > tmp && cat tmp | wc -l";
            System.out.println(cmd);
            proc = Runtime.getRuntime().exec(new String[]{"/bin/sh", "-c", cmd});
            proc.waitFor();
            String err = readOutput(proc.getErrorStream());
            if (err != null && !err.equals("")) throw new Exception("获取测试结果信息失败:" + err);
            int row = 0;
            row = Integer.parseInt(readOutput(proc.getInputStream()).trim());
            System.out.println("tmp文件总行数：" + row);
            int l = 1;
            Map<String,Float> testResults = new HashMap();
            while(l <= row){
                int r;
                if(l + 499 < row)r = l + 499;else r = row;
                String cmd2 = "sed -n '" + l +"," + r + "p' tmp";
                l+=500;
                System.out.println(cmd2);
                proc = Runtime.getRuntime().exec(new String[]{"/bin/sh", "-c", cmd2});
                proc.waitFor();
                String err2 = readOutput(proc.getErrorStream());
                if (err2 != null && !err2.equals("")) throw new Exception("获取测试结果信息失败:" + err2);
                String[] result = readOutput(proc.getInputStream()).split("\n");
                for(String res : result){
                    String[] f = res.split(",");
                    String classname = f[0].split(":")[1].trim();
                    Float time = Float.valueOf(f[2].split(":")[1]);

                    if (testResults.containsKey(classname)) {
                        time += testResults.get(classname);
                    }
                    testResults.put(classname, time + 1);
                }
            }
            if(testResults.size() > 0) JSYDBUtils.batchInsert(testResults,uuid);
        } catch (Exception e) {
            e.printStackTrace();
        }
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
