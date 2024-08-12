package base.third.jenkins;

import base.db.JSYDBUtils;
import ci.benchMark.PR;
import ci.benchMark.TestResultsTaskRelationship;
import com.alibaba.fastjson.JSONObject;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLConnection;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class JenkinsUtils {
    private PR pr;
    //jenkins脚本工作路径
    private String workPath;
    private int seed = 0;

    public JenkinsUtils() {
    }

    public JenkinsUtils(String workPath) {
        this.workPath = workPath;
    }

    public JenkinsUtils(PR pr, String workPath) {
        this.pr = pr;
        this.workPath = workPath;
    }

    private ArrayList<String> selectJobs() {
        ArrayList<String> jobList = new ArrayList<>();
        try {
            String testType = pr.getTask().getTestType();
            String displayId = pr.getDisplayId();
            String displayId_prefix = displayId.split("/")[0].toLowerCase();
            String codeType = null;
            if (pr.getTask().getCodeTypes() != null) codeType = pr.getTask().getCodeTypes()[0];
            if (testType.equals("unitTest")) {
                if (codeType.equals("java")) {
                    //触发分布式计算分支
                    String jdk11Job = "CI_Dispatch/polars_test11_" + displayId_prefix + "_dispatch";
                    System.out.println("jdk11Job:" + jdk11Job);
                    jobList.add(jdk11Job);
                    if (pr.getLLVM()){
                        jobList.add("llvm-polars_test");
                        jobList.add("llvm-polars_test_bi");
                    }
                    String jdk8Job = "polars_test_" + displayId_prefix;
                    System.out.println("jdk8Job:" + jdk8Job);
                    jobList.add(jdk8Job);
                } else if (codeType.equals("c++")) {
                    if (pr.getLLVM()){
                        jobList.add("llvm-polars_test");
                        System.out.println("llvm-polars_test");
                        jobList.add("llvm-polars_test_bi");
                        System.out.println("llvm-polars_test_bi");
                    }

                }
            } else if (testType.equals("benchmarkTest")) {
                jobList.add("polars_test-benchmark");
                System.out.println("polars_test-benchmark");

            } else if (testType.equals("benchmarkTestC")) {
                //C++的benchmark
                jobList.add("llvm-polars_test-benchmark");
                System.out.println("llvm-polars_test-benchmark");
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return jobList;
    }

    //获取相应分支中队列的所有prid，如果跟当前prid相等，就取消该任务，否则分发到任务数最少的分支上
    /*public ArrayList<String> selectParallelJobs() {
        ArrayList<String> jobList = new ArrayList<>();
        try {
            String testType = pr.getTask().getTestType();
            String displayId = pr.getDisplayId();
            String codeType = null;
            if (pr.getTask().getCodeTypes() != null) codeType = pr.getTask().getCodeTypes()[0];
            if (testType.equals("unitTest") && !displayId.toLowerCase().contains("persist")) {
                if (displayId.contains("release")) {
                    //获取相应分支中队列的所有prid
                    Process proc;
                    proc = Runtime.getRuntime().exec("python3 " + workPath + "/jenkinsTool/getQueueInfo.py " + "polars_test11_release_1");
                    proc.waitFor();
                    String outputLines1 = readOutput(proc.getInputStream());
                    if (outputLines1.contains(pr.getPrId())) {
                        seed = -1;
                    }

                    proc = Runtime.getRuntime().exec("python3 " + workPath + "/jenkinsTool/getQueueInfo.py " + "polars_test11_release");
                    proc.waitFor();
                    String outputLines0 = readOutput(proc.getInputStream());
                    if (outputLines0.contains(pr.getPrId())) {
                        seed = -1;
                    }
                    if (seed != -1) {
                        if (outputLines1.length() > outputLines0.length()) seed = 0;
                        else seed = 1;
                    }
                }

                if (seed == 0) {
                    if (codeType.equals("java")) {
                        if (!pr.getIsOnlyHihidataChange()) {
                            jobList.add("polars_test_" + displayId.split("/")[0].toLowerCase());
                            System.out.println("polars_test_" + displayId.split("/")[0].toLowerCase());
                        }
                        jobList.add("polars_test11_" + displayId.split("/")[0].toLowerCase());
                        System.out.println("polars_test11_" + displayId.split("/")[0].toLowerCase());
                        if (pr.getLLVM()) jobList.add("llvm-polars_test");
                        System.out.println("llvm-polars_test");
                    } else if (codeType.equals("c++")) {
                        if (pr.getLLVM()) jobList.add("llvm-polars_test");
                        System.out.println("llvm-polars_test");
                    }
                } else if (seed == 1) {
                    if (codeType.equals("java")) {
                        if (!pr.getIsOnlyHihidataChange()) {
                            jobList.add("polars_test_" + displayId.split("/")[0].toLowerCase() + "_" + seed);
                            System.out.println("polars_test_" + displayId.split("/")[0].toLowerCase() + "_" + seed);
                        }
                        jobList.add("polars_test11_" + displayId.split("/")[0].toLowerCase() + "_" + seed);
                        if (pr.getLLVM()) jobList.add("llvm-polars_test");
                        System.out.println("polars_test11_" + displayId.split("/")[0].toLowerCase() + "_" + seed);
                        System.out.println("llvm-polars_test");
                    } else if (codeType.equals("c++")) {
                        if (pr.getLLVM()) jobList.add("llvm-polars_test");
                        System.out.println("llvm-polars_test");
                    }
                } else if (seed == -1) {
                    //跳过
                }
                //恢复seed = 0
                seed = 0;

            } else if (testType.equals("unitTest") && displayId.toLowerCase().contains("persist")) {
                jobList.add("动态Persist分支");
                System.out.println("动态Persist分支");

            } else if (testType.equals("benchmarkTest")) {
                jobList.add("polars_test-benchmark");
                System.out.println("polars_test-benchmark");

            } else if (testType.equals("benchmarkTestC")) {
                //C++的benchmark
                jobList.add("llvm-polars_test-benchmark");
                System.out.println("llvm-polars_test-benchmark");
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return jobList;
    }*/

    /*public ArrayList<String> selectSerialJobs() {
        ArrayList<String> jobList = new ArrayList<>();
        try {
            String testType = pr.getTask().getTestType();
            String displayId = pr.getDisplayId();
            String codeType = null;
            if (pr.getTask().getCodeTypes() != null) codeType = pr.getTask().getCodeTypes()[0];

            if (testType.equals("unitTest") && !displayId.toLowerCase().contains("persist")) {
                //int seed = (int) breachMap.get(displayId);
                //if (seed == 0 || displayId.equals("persist/3.0")) {
                if (codeType.equals("java")) {
                    if (!pr.getIsOnlyHihidataChange()) {
                        jobList.add("polars_test_" + displayId.split("/")[0].toLowerCase());
                        System.out.println("polars_test_" + displayId.split("/")[0].toLowerCase());
                    }
                    jobList.add("polars_test11_" + displayId.split("/")[0].toLowerCase());
                    if (pr.getLLVM()) jobList.add("llvm-polars_test");
                    System.out.println("polars_test11_" + displayId.split("/")[0].toLowerCase());
                    System.out.println("llvm-polars_test");
                } else if (codeType.equals("c++")) {
                    if (pr.getLLVM()) jobList.add("llvm-polars_test");
                    System.out.println("llvm-polars_test");
                }

            } else if (testType.equals("unitTest") && displayId.toLowerCase().contains("persist")) {
                jobList.add("动态Persist分支");
                System.out.println("动态Persist分支");

            } else if (testType.equals("benchmarkTest")) {
                jobList.add("polars_test-benchmark");
                System.out.println("polars_test-benchmark");

            } else if (testType.equals("benchmarkTestC")) {
                //C++的benchmark
                jobList.add("llvm-polars_test-benchmark");
                System.out.println("llvm-polars_test-benchmark");
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return jobList;
    }*/

    public void getQueuesNumber(PR pr, String cookie) throws Exception {

        String res = "任务开始:";
        /*
        Process proc;
        String res = "排队数:\n";
        int consume = 0;
        proc = Runtime.getRuntime().exec("python3 " + workPath + "/jenkinsTool/getQueueInfo.py " + "polars_test11_release");
        proc.waitFor();
        String outputLines0 = readOutput(proc.getInputStream());
        proc = Runtime.getRuntime().exec("python3 " + workPath + "/jenkinsTool/getQueueInfo.py " + "polars_test11_release_1");
        proc.waitFor();
        String outputLines1 = readOutput(proc.getInputStream());
        System.out.println("outputLines1:" + outputLines1);
        int count0;
        int count1;
        if (outputLines0 != null && !outputLines0.equals("[]")) {
            count0 = outputLines0.split(",").length + 1;
        } else {
            count0 = 0;
        }
        if (outputLines1 != null && !outputLines1.equals("[]")) {
            count1 = outputLines1.split(",").length + 1;
        } else {
            count1 = 0;
        }
        int count = count0 + count1;
        res += "relase分支:" + count + "\n";
        consume += (count * 1);

        proc = Runtime.getRuntime().exec("python3 " + workPath + "/jenkinsTool/getQueueInfo.py " + "polars_test11_feature");
        proc.waitFor();
        outputLines0 = readOutput(proc.getInputStream());
        if (outputLines0 != null && !outputLines0.equals("[]")) {
            count = outputLines0.split(",").length + 1;
        } else {
            count = 0;
        }
        res += "feature分支:" + count + "\n";
        consume += (count * 1);

        proc = Runtime.getRuntime().exec("python3 " + workPath + "/jenkinsTool/getQueueInfo.py " + "llvm-polars_test");
        proc.waitFor();
        outputLines0 = readOutput(proc.getInputStream());
        if (outputLines0 != null && !outputLines0.equals("[]")) {
            count = outputLines0.split(",").length + 1;
        } else {
            count = 0;
        }
        res += "c++单测:" + count + "\n";
        consume += (count * 1);

        proc = Runtime.getRuntime().exec("python3 " + workPath + "/jenkinsTool/getQueueInfo.py " + "polars_test-benchmark");
        proc.waitFor();
        outputLines0 = readOutput(proc.getInputStream());
        if (outputLines0 != null && !outputLines0.equals("[]")) {
            count = outputLines0.split(",").length + 1;
        } else {
            count = 0;
        }
        res += "benchmark:" + count + "\n";
        consume += (count * 0.5);

        proc = Runtime.getRuntime().exec("python3 " + workPath + "/jenkinsTool/getQueueInfo.py " + "llvm-polars_test-benchmark");
        proc.waitFor();
        outputLines0 = readOutput(proc.getInputStream());
        if (outputLines0 != null && !outputLines0.equals("[]")) {
            count = outputLines0.split(",").length + 1;
        } else {
            count = 0;
        }
        res += "c++的benchmark:" + count + "\n";
        consume += (count * 0.5);

        res += "预计执行开始耗时:" + consume / 3 + "H";
*/

        String url = "https://code.fineres.com/rest/api/latest/projects/CAL/repos/polars/pull-requests/" + pr.getPrId() + "/comments?diffType=EFFECTIVE&markup=true&avatarSize=48";
        URLConnection urlConnection = new URL(url).openConnection();
        urlConnection.setRequestProperty("Cookie", cookie);
        HttpURLConnection connection = (HttpURLConnection) urlConnection;
        connection.setRequestMethod("POST");
        connection.setDoInput(true);
        connection.setDoOutput(true);
        connection.setRequestProperty("Referer", "https://code.fineres.com/projects/CAL/repos/polars/pull-requests/1742/overview");
        connection.setRequestProperty("Content-Type", "application/json");
        JSONObject json = new JSONObject();
        String text = res;
        json.put("text", text);
        json.put("severity", "NORMAL");
        OutputStreamWriter writer = new OutputStreamWriter(connection.getOutputStream(), "UTF-8");
        writer.write(json.toString());
        writer.flush();

        connection.connect();
        if (connection.getResponseCode() == 201)
            System.out.println("请求正常");
        else
            System.out.println("请求失败");

    }

    public void buildJenkinsBuild() {
        try {
            //CI改为分布式计算，preTest只负责触发任务，不负责调度
            ArrayList<String> jobList = selectJobs();

            //轮询job,并行执行
            //ArrayList<String> jobList = selectParallelJobs();
            //串行执行
            //ArrayList<String> jobList = selectSerialJobs();
            //通过shell调用python api
            Process proc = null;
            String builder = pr.getBuilder();
            String prId = pr.getPrId();
            String displayId = pr.getDisplayId();
            for (String job : jobList) {
                if (job.equals("polars_test-benchmark") || job.equals("llvm-polars_test-benchmark")) {
                    for (String dataType : pr.getTask().getDataTypes()) {
                        String cmd = "python3 " + workPath + "/jenkinsTool/jenkins_api.py " + job + " " + builder + " " + prId + " " + displayId + " " + dataType;
                        System.out.println(cmd);
                        proc = Runtime.getRuntime().exec(cmd);
                    }
                } else {
                    String cmd = "python3 " + workPath + "/jenkinsTool/jenkins_api.py " + job + " " + builder + " " + prId + " " + displayId.toLowerCase() + " " + pr.getIsOnlyHihidataChange() + " " + pr.getIsContainBIChange() + " " + pr.getIsContainHihidataChange();
                    System.out.println(cmd);
                    proc = Runtime.getRuntime().exec(cmd);
                }
                proc.waitFor();
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void buildOperatorBuild(List<TestResultsTaskRelationship> modules, String uuid, String workPath, String builder, String prId, String storagePath, String branch, String isContainBIChange, String isContainHihidataChange) {
        try {
            //由于类名前缀可能过大，所以类名前缀需要保存到文件中，而不是通过变量传输
            Process proc = null;
            for (TestResultsTaskRelationship m : modules) {
                int number = 1;
                //代表是否成功创建文件
                boolean key = false;
                try {
                    File file = null;
                    while (!key) {
                        String fileName = storagePath + "CIInformation/" + uuid + "_" + m.getJobName() + "_" + (number++) + ".txt";
                        System.out.println("文件路径:" + fileName);
                        file = new File(fileName);
                        key = file.createNewFile();
                        if (!key) System.out.println("文件已创建：" + fileName);
                    }

                    // 将数据写入文件
                    FileWriter fileWriter = new FileWriter(file);
                    BufferedWriter bufferedWriter = new BufferedWriter(fileWriter);
                    bufferedWriter.write(m.getClassNameStr());

                    bufferedWriter.close();
                    fileWriter.close();
                } catch (Exception e) {
                    System.out.println("发生错误：" + e.getMessage());
                    e.printStackTrace();
                }

                String cmd = "python3 " + workPath + "/jenkinsTool/jenkins_buildOperator.py " + m.getJobName() + " " + uuid + " " + builder + " " + prId + " " + branch + " " + --number + " " + isContainBIChange + " " + isContainHihidataChange;
                System.out.println("上面的" + cmd);
                System.out.println(m.getJobName() + "执行耗时:" + m.getTotalTime());
                retry(cmd);

                //将触发的任务记录到数据库中
                JSYDBUtils.updateData("insert into CI_Schedul_Information (uuid, sonJobName, number, isFinish) value (\"" + uuid + "\",\"" + m.getJobName() + "\"," + number + "," + false + ");");
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void retry(String cmd) throws InterruptedException, IOException {
        Process proc;
        //增加重试逻辑
        int maxRetries = 3;
        int retryCount = 0;
        while (retryCount < maxRetries) {
            proc = Runtime.getRuntime().exec(cmd);
            proc.waitFor();
            String err = readOutput(proc.getErrorStream());
            if (err != null && !err.equals("")) {
                retryCount++;
            } else {
                break;
            }
        }
    }


    public void killRepeatBuild() {
        try {
            Process proc = Runtime.getRuntime().exec("python3 " + workPath + "/jenkinsTool/jenkins_KillBuild.py " + pr.getPrId() + " " + pr.getDisplayId().split("/")[0]);
            proc.waitFor();
        } catch (IOException | InterruptedException e) {
            e.printStackTrace();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }


    public int getAllSonJobsCount(String sonJobsName) {
        Process proc;
        int count = 0;
        for (int attempt = 0; attempt < 10; attempt++) {
            try {
                proc = Runtime.getRuntime().exec("python3 " + workPath + "/jenkinsTool/getSonJobsName.py");
                proc.waitFor();
                String jobsName = readOutput(proc.getInputStream());
                for (String jobName : jobsName.split("\n")) {
                    if (jobName.contains(sonJobsName)) {
                        count++;
                    }
                }
                if(count != 0){
                    break;
                }
                System.out.println("重试" + attempt + "次");
                Thread.sleep(1000);
            } catch (IOException | InterruptedException e) {
                e.printStackTrace();
            }
        }

        System.out.println("总共" + count + "个TestOperator节点");
        return count;
    }

    public Map<String, Integer> getAllSonJobsNumberOfQueues(String sonJobsName, int N) {
        Process proc;
        Map<String, Integer> sonJobsNumberOfQueues = new HashMap<>();
        int count = getAllSonJobsCount(sonJobsName);

        try {
            for (int number = 1; number <= count; number++) {
                String sonJobName = sonJobsName + number;
                proc = Runtime.getRuntime().exec("python3 " + workPath + "/jenkinsTool/getQueueInfo_uuid.py " + sonJobName);
                proc.waitFor();
                String result = readOutput(proc.getInputStream());
                int c;
                if (result != null && !result.contains("[]")) {
                    c = result.split(",").length + N + 1;
                } else {
                    c = 0 + N + 1;
                }

                sonJobsNumberOfQueues.put(sonJobName, c);
            }

        } catch (IOException | InterruptedException e) {
            e.printStackTrace();
        }
        return sonJobsNumberOfQueues;
    }

    private static String readOutput(InputStream inputStream) throws IOException {
        String outputLines = null;
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream))) {
            String line;
            while ((line = reader.readLine()) != null) {
                outputLines += (line + "\n");
            }
        }
        return outputLines;
    }
}
