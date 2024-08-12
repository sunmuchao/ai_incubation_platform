package ci.benchMark;

import base.db.JSYDBUtils;
import base.third.jenkins.JenkinsUtils;
import com.alibaba.fastjson.JSONObject;
import com.google.common.base.Joiner;
import com.moandjiezana.toml.Toml;

import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLConnection;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.TreeMap;
import java.util.stream.Collectors;

import static ci.benchMark.AddComment.getCookie;

/**
 * @author sunmuchao
 * @date 2023/9/26 11:17 上午
 */
public class Scheduler {
    public static void main(String[] args) throws Exception {
        //当前dispatch的job名
        String jobName = args[0];
        //当前dispatch的构建ID，用于拼接uuid确定唯一的任务
        int buildId = Integer.parseInt(args[1]);
        //要触发算子的名称(不包含编号)
        String sonJobName = args[2];
        //以"/"结尾
        String jenkinsPath = args[3];
        String workPath = args[4];
        //存储路径
        String storagePath = args[5];
        //builder
        String builder = args[6];
        //prId
        String prId = args[7];
        //分支名
        String branch = args[8];
        //是否包含BI模块改变
        String isContainBIChange = args[9];
        //是否仅包含九数云模块改变
        boolean isOnlyHihidataChange = Boolean.parseBoolean(args[10]);
        //是否包含Hihidata模块改变
        String isContainHihidataChange = args[11];

        Path projectPath = Paths.get(jenkinsPath, "CI_Dispatch", jobName);

        Path patchPath = Paths.get(storagePath, "Patch", "polars-" + prId + ".patch");

        String uuid = jobName + "_" + buildId;

        //增加review流程
        coreClassNotify(projectPath, patchPath, prId);
        List<TestResult> result = null;

        result = addNewTestClass(getLastResult(result, buildId, jobName), projectPath, Paths.get(workPath));

        JenkinsUtils jenkinsUtils = new JenkinsUtils(workPath);

        //分发到N个节点上
        int N = 4;

        Map<String, Integer> sonJobs = jenkinsUtils.getAllSonJobsNumberOfQueues(sonJobName, N);

        //选择最少任务的N个operator
        Map<String, Integer> selectedJobs = selectTopNMinValues(sonJobs, N);


        List<TestResultsTaskRelationship> modules = sortTestResultsTaskRelationship(classifyModule(result, selectedJobs.size()));

        //绑定任务编号
        for (int i = 0; i < modules.size(); i++) {
            modules.get(i).setTaskName("task" + i);
            selectedJobs.put("task" + i, 1);
        }

        //将任务绑定到job上
        modules = BindTaskToJob(selectedJobs, modules, N);

        //将代码移动到CodeStorage存储下
        copyProject(projectPath, storagePath, uuid);

        //modules 中存放着job和modules的对应关系
        //触发对应的job，并传递modules参数
        jenkinsUtils.buildOperatorBuild(modules, uuid, workPath, builder, prId, storagePath, branch, isContainBIChange, isContainHihidataChange);
    }

    public static List<TestResult> getLastResult(List<TestResult> result, int buildId, String jobName) {
        //获取上次各个模块的耗时,如果上一次没有执行成功,则获取上上一次的，直到成功为止
        for (int i = 1; i <= buildId; i++) {
            int last_buildId = buildId - i;
            String last_uuid = jobName + "_" + last_buildId;
            result = JSYDBUtils.queryTestResult("select class_name_prefix,time FROM test_results where uuid = \"" + last_uuid + "\"");
            if (result.size() > 0) break;
        }
        return result;
    }

    private static void coreClassNotify(Path projectPath, Path PatchPath, String prId) {
        //当前目录下包含代码，只需要去拿到Patch信息即可
        //首先获取当前目录下的FrameworkCoreClass类
        //解析toml文件
        PriorityCoreClasses pcc = parseFrameworkCoreClass(projectPath);
        //获取Patch文件，查看core类是否有更改
        PriorityCoreClassesRs pccrs = CheckChangesToCoreClasses(pcc, PatchPath);
        if (pccrs != null) {
            //发送结果通知
            sendResult(prId, pccrs);
        }
    }

    private static void sendResult(String prId, PriorityCoreClassesRs pccrs) {

        try {
            List<String> highPriorityCoreClasses = pccrs.getHighPriorityCoreClasses();
            List<String> mediumPriorityCoreClasses = pccrs.getMediumPriorityCoreClasses();
            List<String> lowPriorityCoreClasses = pccrs.getLowPriorityCoreClasses();
            if (highPriorityCoreClasses.size() > 0 || mediumPriorityCoreClasses.size() > 0 || lowPriorityCoreClasses.size() > 0) {
                String url = "https://code.fineres.com/rest/api/latest/projects/CAL/repos/polars/pull-requests/" + prId + "/comments?diffType=EFFECTIVE&markup=true&avatarSize=48";
                URLConnection urlConnection = new URL(url).openConnection();
                String rememberme = getCookie();
                urlConnection.setRequestProperty("Cookie", rememberme);
                HttpURLConnection connection = (HttpURLConnection) urlConnection;
                connection.setRequestMethod("POST");
                connection.setDoInput(true);
                connection.setDoOutput(true);
                connection.setRequestProperty("Referer", "https://code.fineres.com/projects/CAL/repos/polars/pull-requests/1742/overview");
                connection.setRequestProperty("Content-Type", "application/json");
                JSONObject json = new JSONObject();
                StringBuilder text = new StringBuilder();

                //展示结果
                String result = null;
                if (highPriorityCoreClasses.size() > 0) {
                    text.append("重要提醒: High核心文件:");
                    result = Joiner.on(",").join(highPriorityCoreClasses);
                    text.append(result + "被改动!!!\n");
                }

                if (mediumPriorityCoreClasses.size() > 0) {
                    text.append("重要提醒: Medium核心文件:");
                    result = Joiner.on(",").join(mediumPriorityCoreClasses);
                    text.append(result + "被改动!!!\n");
                }

                if (lowPriorityCoreClasses.size() > 0) {
                    text.append("重要提醒: Low核心文件:");
                    result = Joiner.on(",").join(lowPriorityCoreClasses);
                    text.append(result + "被改动!!!\n");
                }

                System.out.println("text:" + text);
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

        } catch (IOException e) {
            e.printStackTrace();
        }
    }


    private static PriorityCoreClassesRs CheckChangesToCoreClasses(PriorityCoreClasses pcc, Path PatchPath) {
        Process process;
        try {
            String command = "grep \"diff --git\" " + PatchPath + " | awk -F \" \" '{print $4}'";
            System.out.println(command);

            process = Runtime.getRuntime().exec(new String[]{"/bin/sh", "-c", command});
            Thread waitForProcessThread = new Thread(() -> {
                try {
                    process.waitFor();
                } catch (InterruptedException e) {
                    // 进程被中断
                    e.printStackTrace();
                }
            });

            waitForProcessThread.start();
            long timeoutMillis = 60000; // 60秒
            waitForProcessThread.join(timeoutMillis);
            if (waitForProcessThread.isAlive()) {
                process.destroy();
                waitForProcessThread.interrupt();
                return null;
            }

            BufferedReader br = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String className;

            while ((className = br.readLine()) != null) {
                System.out.println(className);
                pcc.JudgePriority(className);
            }

            return pcc.getPriorityCoreClassesRs();

        } catch (IOException | InterruptedException e) {
            e.printStackTrace();
        }
        return null;
    }

    private static PriorityCoreClasses parseFrameworkCoreClass(Path projectPath) {
        Path frameworkCoreClassPath = Paths.get(String.valueOf(projectPath), "FrameworkCoreClass.toml");

        if (frameworkCoreClassPath == null || !Files.exists(frameworkCoreClassPath)) {
            return new PriorityCoreClasses();
        }

        // 读取TOML文件
        Toml toml = new Toml().read(new File(frameworkCoreClassPath.toString()));

        PriorityCoreClasses pcc = new PriorityCoreClasses();

        // 解析不同优先级的配置
        String[] priorities = {"High", "Medium", "Low"};

        for (String priority : priorities) {
            String className = toml.getTable(priority).getString("files");
            if (className != null && !className.trim().equals("")) {
                List classNames = Arrays.asList(className.split(","));

                if (priority.equals("High")) {
                    pcc.setHighPriorityCoreClasses(classNames);
                } else if (priority.equals("Medium")) {
                    pcc.setMediumPriorityCoreClasses(classNames);
                } else if (priority.equals("Low")) {
                    pcc.setLowPriorityCoreClasses(classNames);
                }
            }
        }
        return pcc;
    }

    public static List<TestResultsTaskRelationship> BindTaskToJob(Map<String, Integer> sonJobs, List<TestResultsTaskRelationship> modules, int N) {
        //把task 和 job放入到JobTask中
        List<JobTask> tmp = new ArrayList<>();
        for (Entry entry : sonJobs.entrySet()) {
            JobTask jobTask = new JobTask((String) entry.getKey(), Float.valueOf(String.valueOf(entry.getValue())));
            tmp.add(jobTask);
        }

        //对task 和 job进行均分
        List<List<JobTask>> jobTaskList = getAvgArr2(tmp, N);

        for (TestResultsTaskRelationship module : modules) {
            String taskName = module.getTaskName();
            String jobName = null;
            for (List<JobTask> jts : jobTaskList) {
                boolean key = false;
                for (JobTask jt : jts) {
                    if (jt.getName().equals(taskName)) {
                        key = true;
                    }
                }
                for (JobTask jt : jts) {
                    if (!jt.getName().contains("task") && key) {
                        jobName = jt.getName();
                    }
                }
            }
            module.setJobName(jobName);
        }

        return modules;
    }

    public static List<TestResult> addNewTestClass(List<TestResult> testResults, Path projectPath,Path workPath) throws Exception {
        String cmd;
        Process proc;
        /*if (isOnlyHihidataChange == true) {
            cmd = "grep -rl --include=\"*.java\" '@Test' " + projectPath + "/polars-hihidata | while read -r file; do package=$(grep -m 1 '^package ' \"$file\" | sed 's/^package \\(.*\\);/\\1/'); filename=$(basename \"$file\"); echo \"$package.$filename\"; done > tmp && cat tmp | wc -l";
        } else {
            cmd = "grep -rl --include=\"*.java\" '@Test' " + projectPath + " | while read -r file; do package=$(grep -m 1 '^package ' \"$file\" | sed 's/^package \\(.*\\);/\\1/'); filename=$(basename \"$file\"); echo \"$package.$filename\"; done > tmp && cat tmp | wc -l";
        }*/
        cmd = "python3 " + workPath + "/GetTestClass.py " + projectPath;
        System.out.println(cmd);
        proc = Runtime.getRuntime().exec(new String[]{"/bin/sh", "-c", cmd});
        proc.waitFor();
        String err = readOutput(proc.getErrorStream());
        if (err != null && !err.equals("")) throw new Exception("获取测试文件信息失败:" + err);
        int row = Integer.parseInt(readOutput(proc.getInputStream()).trim());
        System.out.println("tmp文件行数:" + row);
        int l = 1;
        List<TestResult> tmp = new ArrayList<>();
        while (l <= row) {
            int r;
            if (l + 499 < row) r = l + 499;
            else r = row;
            String cmd2 = "sed -n '" + l + "," + r + "p' tmp";
            l += 500;
            System.out.println(cmd2);
            proc = Runtime.getRuntime().exec(new String[]{"/bin/sh", "-c", cmd2});
            proc.waitFor();
            String err2 = readOutput(proc.getErrorStream());
            if (err2 != null && !err2.equals("")) throw new Exception("获取测试文件信息失败:" + err2);
            String[] out = readOutput(proc.getInputStream()).split("\n");
            for (String o : out) {
                o = o.substring(0, o.length() - 5);
                tmp.add(new TestResult(o, 1F));
            }
        }
        List<TestResult> distinctResults = tmp.stream()
                .distinct()
                .collect(Collectors.toList());
        // 找出tmp中新增的TestResult对象
        List<TestResult> finalTestResults = testResults;
        List<TestResult> newResults = distinctResults.stream()
                .filter(result -> !finalTestResults.contains(result))
                .collect(Collectors.toList());
        System.out.println("新增测试类的数量:" + newResults.size());
        testResults.retainAll(distinctResults);
        testResults.addAll(newResults);
        System.out.println("--------");

        testResults = testResults.stream()
                .collect(Collectors.toList());

        int testResultTimeEqualZero = 0;
        for (TestResult testResult : testResults) {
            if(testResult.getTime() == 0) testResultTimeEqualZero ++;
        }
        System.out.println("单测类耗时等于0的数量: " + testResultTimeEqualZero);
        return testResults;
    }

    public static void copyProject(Path projectPath, String storagePath, String uuid) throws Exception {
        // 将代码移动到 CodeStorage 存储下
        System.out.println("开始将代码移动到 CodeStorage 存储下");
        String destination = storagePath + "CodeStorage/" + uuid;
        String cmd = "mkdir -p " + destination + " && rsync -av --exclude='polars-llvm/docker/internal/' " + projectPath + "/* " + destination
                + " && mkdir -p " + destination + "/polars-llvm/docker/internal/output/"
                + " && rsync -av " + projectPath + "/polars-llvm/docker/internal/output/ " + destination + "/polars-llvm/docker/internal/output/";
        System.out.println(cmd);
        Process proc = Runtime.getRuntime().exec(new String[]{"/bin/sh", "-c", cmd});

        // 启动线程读取标准输出和错误流
        StreamGobbler outputGobbler = new StreamGobbler(proc.getInputStream(), "OUTPUT");
        StreamGobbler errorGobbler = new StreamGobbler(proc.getErrorStream(), "ERROR");

        outputGobbler.start();
        errorGobbler.start();

        int exitCode = proc.waitFor();
        outputGobbler.join();
        errorGobbler.join();

        if (exitCode != 0) {
            throw new Exception("移动到 CodeStorage 失败的错误信息: " + errorGobbler.getOutput());
        }
    }

    // 辅助类用于读取流
    private static class StreamGobbler extends Thread {
        private InputStream inputStream;
        private String streamType;
        private StringBuilder output;

        public StreamGobbler(InputStream inputStream, String streamType) {
            this.inputStream = inputStream;
            this.streamType = streamType;
            this.output = new StringBuilder();
        }

        @Override
        public void run() {
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    output.append(line).append("\n");
                    if (streamType.equals("ERROR")) {
                        System.err.println(line);
                    } else {
                        System.out.println(line);
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        }

        public String getOutput() {
            return output.toString();
        }
    }


    private static List<TestResultsTaskRelationship> sortTestResultsTaskRelationship(List<TestResultsTaskRelationship> modules) {
        // 创建自定义比较器，按TotalExecutionTime字段从大到小排序
        Comparator<TestResultsTaskRelationship> comparator = new Comparator<TestResultsTaskRelationship>() {
            @Override
            public int compare(TestResultsTaskRelationship module1, TestResultsTaskRelationship module2) {
                // 从大到小排序
                return Double.compare(module2.getTotalTime(), module1.getTotalTime());
            }
        };

        // 使用Collections.sort()方法排序List
        Collections.sort(modules, comparator);
        return modules;
    }


    private static List<TestResultsTaskRelationship> classifyModule(List<TestResult> result, int size) {
        //根据result的time字段直接排序，
        List<List<TestResult>> avgArr = getAvgArr(result, size);
        List<TestResultsTaskRelationship> TestResultsTaskRelationships = new ArrayList<>();
        for (List<TestResult> testResultList : avgArr) {
            TestResultsTaskRelationship TestResultsTaskRelationship = new TestResultsTaskRelationship(testResultList);
            TestResultsTaskRelationships.add(TestResultsTaskRelationship);
        }
        return TestResultsTaskRelationships;
    }

    //均分算法，将一组数据尽可能均匀的分成arrNum份
    public static List<List<TestResult>> getAvgArr(List<TestResult> testResultList, int arrNum) {
        List<List<TestResult>> avgArrays = new ArrayList<>();
        if (testResultList.size() == 0 || testResultList.size() < arrNum) {
            return avgArrays;
        }

        // 1. 计算平均值
        double sum = 0;
        double mean;
        for (TestResult testResult : testResultList) {
            sum += testResult.getTime();
        }
        mean = sum / arrNum;

        Collections.sort(testResultList, new Comparator<TestResult>() {
            @Override
            public int compare(TestResult result1, TestResult result2) {
                // 根据时间进行比较，倒序排序
                return Double.compare(result2.getTime(), result1.getTime());
            }
        });

        for (int cnt = 0; cnt < arrNum; cnt++) {
            List<TestResult> arr = new ArrayList<>();
            if (cnt == arrNum - 1) {
                // 最后一组，返回数组剩余所有数
                avgArrays.add(testResultList);
                break;
            }

            // 如果最大的数max>=mean，这个数单独一个组
            if (!testResultList.isEmpty() && testResultList.get(0).getTime() >= mean) {
                arr.add(testResultList.get(0));
                avgArrays.add(arr);
                sum -= testResultList.get(0).getTime();

                // 重新计算剩下partition的平均值
                mean = sum / (arrNum - arr.size());
            } else {
                // 否则寻找一组数据
                ArrayList<TestResult> result = getList(testResultList, mean, Math.pow(mean, 2));
                for (TestResult item : result) {
                    arr.add(item);
                }
                avgArrays.add(arr);
            }
            // 将已经形成一组的数据从原数组中移除，准备寻找下一组数据
            testResultList.removeAll(arr);
        }

        return avgArrays;
    }

    public static ArrayList<TestResult> getList(List<TestResult> arr, double delta, double distance) {
        List<TestResult> res = new ArrayList<>();
        if (arr.isEmpty()) {
            return new ArrayList<TestResult>();
        }

        for (int i = 0; i < arr.size() - 1; i++) {
            if (delta == arr.get(i).getTime()) {
                res.add(arr.get(i));
                return (ArrayList<TestResult>) res;
            } else if (delta < arr.get(i).getTime()) {
                continue;
            } else if (delta > arr.get(i).getTime()) {
                if (i == 0) {
                    res.add(arr.get(i));
                    delta = delta - arr.get(i).getTime();
                    distance = Math.pow(delta, 2);
                    ArrayList<TestResult> tmp = getList(arr.subList(i + 1, arr.size()), delta, distance);
                    for (TestResult item : tmp) {
                        res.add(item);
                    }
                    return (ArrayList<TestResult>) res;
                } else {
                    double dis1 = Math.pow(arr.get(i - 1).getTime() - delta, 2);
                    double dis2 = Math.pow(delta - arr.get(i).getTime(), 2);
                    if (dis1 > dis2) {
                        res.add(arr.get(i));
                        delta = delta - arr.get(i).getTime();
                        ArrayList<TestResult> tmp = getList(arr.subList(i + 1, arr.size()), delta, dis2);
                        for (TestResult item : tmp) {
                            res.add(item);
                        }
                        return (ArrayList<TestResult>) res;
                    } else {
                        ArrayList<TestResult> tmp = getList(arr.subList(i, arr.size()), delta, dis2);
                        double dis = dis1;
                        if (dis1 > dis2) {
                            for (TestResult item : tmp) {
                                res.add(item);
                            }
                            return (ArrayList<TestResult>) res;
                        }
                        res.add(arr.get(i - 1));
                        return (ArrayList<TestResult>) res;
                    }
                }
            }
        }

        double dis = Math.pow(delta - arr.get(arr.size() - 1).getTime(), 2);

        if (dis < distance) {
            List res2 = new ArrayList<TestResult>();
            res2.add(arr.get(arr.size() - 1));
            return (ArrayList<TestResult>) res2;
        }

        return new ArrayList<>();
    }


    //均分算法，将一组数据尽可能均匀的分成arrNum份
    public static List<List<JobTask>> getAvgArr2(List<JobTask> jobTaskList, int arrNum) {
        List<List<JobTask>> avgArrays = new ArrayList<>();
        if (jobTaskList.size() == 0 || jobTaskList.size() < arrNum) {
            return avgArrays;
        }

        // 1. 计算平均值
        double sum = 0;
        double mean;
        for (JobTask jobTask : jobTaskList) {
            sum += jobTask.getTime();
        }
        mean = sum / arrNum;

        Collections.sort(jobTaskList, new Comparator<JobTask>() {
            @Override
            public int compare(JobTask result1, JobTask result2) {
                // 根据时间进行比较，倒序排序
                return Double.compare(result2.getTime(), result1.getTime());
            }
        });

        for (int cnt = 0; cnt < arrNum; cnt++) {
            List<JobTask> arr = new ArrayList<>();
            if (cnt == arrNum - 1) {
                // 最后一组，返回数组剩余所有数
                avgArrays.add(jobTaskList);
                break;
            }

            // 如果最大的数max>=mean，这个数单独一个组
            if (!jobTaskList.isEmpty() && jobTaskList.get(0).getTime() >= mean) {
                arr.add(jobTaskList.get(0));
                avgArrays.add(arr);
                sum -= jobTaskList.get(0).getTime();

                // 重新计算剩下partition的平均值
                mean = sum / (arrNum - arr.size());
            } else {
                // 否则寻找一组数据
                ArrayList<JobTask> result = getList2(jobTaskList, mean, Math.pow(mean, 2));
                for (JobTask item : result) {
                    arr.add(item);
                }
                avgArrays.add(arr);
            }
            // 将已经形成一组的数据从原数组中移除，准备寻找下一组数据
            jobTaskList.removeAll(arr);
        }

        return avgArrays;
    }

    public static ArrayList<JobTask> getList2(List<JobTask> arr, double delta, double distance) {
        List<JobTask> res = new ArrayList<>();
        if (arr.isEmpty()) {
            return new ArrayList<JobTask>();
        }

        for (int i = 0; i < arr.size() - 1; i++) {
            if (delta == arr.get(i).getTime()) {
                res.add(arr.get(i));
                return (ArrayList<JobTask>) res;
            } else if (delta < arr.get(i).getTime()) {
                continue;
            } else if (delta > arr.get(i).getTime()) {
                if (i == 0) {
                    res.add(arr.get(i));
                    delta = delta - arr.get(i).getTime();
                    distance = Math.pow(delta, 2);
                    ArrayList<JobTask> tmp = getList2(arr.subList(i + 1, arr.size()), delta, distance);
                    for (JobTask item : tmp) {
                        res.add(item);
                    }
                    return (ArrayList<JobTask>) res;
                } else {
                    double dis1 = Math.pow(arr.get(i - 1).getTime() - delta, 2);
                    double dis2 = Math.pow(delta - arr.get(i).getTime(), 2);
                    if (dis1 > dis2) {
                        res.add(arr.get(i));
                        delta = delta - arr.get(i).getTime();
                        ArrayList<JobTask> tmp = getList2(arr.subList(i + 1, arr.size()), delta, dis2);
                        for (JobTask item : tmp) {
                            res.add(item);
                        }
                        return (ArrayList<JobTask>) res;
                    } else {
                        ArrayList<JobTask> tmp = getList2(arr.subList(i, arr.size()), delta, dis2);
                        double dis = dis1;
                        if (dis1 > dis2) {
                            for (JobTask item : tmp) {
                                res.add(item);
                            }
                            return (ArrayList<JobTask>) res;
                        }
                        res.add(arr.get(i - 1));
                        return (ArrayList<JobTask>) res;
                    }
                }
            }
        }

        double dis = Math.pow(delta - arr.get(arr.size() - 1).getTime(), 2);

        if (dis < distance) {
            List res2 = new ArrayList<JobTask>();
            res2.add(arr.get(arr.size() - 1));
            return (ArrayList<JobTask>) res2;
        }

        return new ArrayList<>();
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


    public static Map<String, Integer> selectTopNMinValues(Map<String, Integer> map, int n) {
        // 使用一个 TreeMap 来按 value 进行排序
        TreeMap<Integer, List<String>> sortedByValue = new TreeMap<>();

        // 遍历原始 Map，将 key 按照对应的 value 放入 TreeMap 中
        for (Map.Entry<String, Integer> entry : map.entrySet()) {
            String key = entry.getKey();
            Integer value = entry.getValue();

            // 如果 TreeMap 中没有当前 value 对应的 List，则创建一个新的 List
            if (!sortedByValue.containsKey(value)) {
                sortedByValue.put(value, new ArrayList<>());
            }

            // 将当前 key 加入到 value 对应的 List 中
            sortedByValue.get(value).add(key);
        }

        // 创建一个新的 Map 用于存放选出的前 N 个最小值的 key
        Map<String, Integer> result = new LinkedHashMap<>();
        int count = 0;

        // 遍历 TreeMap（已按照 value 排序），将前 N 个最小值的 key 放入 result Map 中
        for (Map.Entry<Integer, List<String>> entry : sortedByValue.entrySet()) {
            Integer value = entry.getKey();
            List<String> keys = entry.getValue();

            // 遍历当前 value 对应的所有 key
            for (String key : keys) {
                result.put(key, value);
                count++;

                // 如果已经选出了前 N 个最小值的 key，则返回结果
                if (count >= n) {
                    return result;
                }
            }
        }

        return result; // 如果原始 Map 中的 key 不足 N 个，则返回已选出的所有 key
    }

    private static boolean containsModule(List<TestResultsTaskRelationship> tmpModules, TestResultsTaskRelationship tmpModule) {
        for (TestResultsTaskRelationship module : tmpModules) {
            // Assuming you have an equals method defined in TestResultsTaskRelationship class
            if (module.equals(tmpModule)) {
                return true; // tmpModule found in tmpModules
            }
        }
        return false; // tmpModule not found in tmpModules
    }
}
