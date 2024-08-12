package ci.benchMark;

import base.db.DBUtils;
import base.db.JSYDBUtils;
import base.third.bitBucket.BitBucketUtils;
import base.third.jenkins.JenkinsUtils;
import base.third.jira.JiraUtils;
import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;

import java.io.*;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.Date;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

public class PreTest {
    static List<String> persistTaskCache = new ArrayList<>();
    static final ExecutorService executorService = Executors.newSingleThreadExecutor();

    public static PR getPr(String filepath, BitBucketUtils bitBucketUtils, List<String> branchNames) throws Exception {
        List<PR> prids = new ArrayList<>();
        List<String> oldPrids = new ArrayList<>();
        Set<String> newprids = new HashSet<>();
        Boolean isTargetBranch = false;
        PR todealPr = null;
        String url = "https://code.fineres.com/projects/CAL/repos/polars/pull-requests";
        try {
            //在getResponse前获取当前时间，防止当前时间getResponse过慢导致触发失败
            long currDate = System.currentTimeMillis() / 1000;
            StringBuffer response = bitBucketUtils.getResponse(url);
            if (response.length() == 0) return null;
            JSONArray jsonArray = JSON.parseArray(response.toString().split("initialData")[1].split("\"values\":")[1].split(",\"start\":")[0]);
            //System.out.println("jsonArray:"+jsonArray);

            for (int i = 0; i < jsonArray.size(); i++) {
                JSONObject jsonObject = jsonArray.getJSONObject(i);
                String prId = jsonObject.getString("id");
                String displayId = ((JSONObject) JSON.parse(jsonObject.getString("toRef"))).getString("displayId");
                String builder = ((JSONObject) JSON.parse(((JSONObject) (JSON.parse(jsonObject.getString("author")))).getString("user"))).getString("displayName");
                //如果是superman的话，代表是逆合并，不需要跑单测
                if(builder.contains("superman")){
                    continue;
                }

                PR pr = new PR(displayId, builder, prId);

                String updatedDate = jsonObject.getString("updatedDate");
                pr.setUpdatedDatelong(updatedDate);
                pr.setState(jsonObject.getString("state"));


                //判断是否是persist分支，如果是的话就创建任务，防止其他分支遗漏bug
                persistCreateTaskAsync(pr);

                //判断是否有手动触发以及是否触发benchmark测试:0:java单测 1:java非字典的benchmark 2:java字典的benchmark 3:c++单测 4:c++的benchmark
                Boolean[] isTriggers = bitBucketUtils.monitorManualTriggers(pr);

                SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
                System.out.println(
                        "prid:" + pr.getPrId() +
                                " 当前时间:" + sdf.format(new Date()) +
                                " 创建pr时间:" + sdf.format(pr.getOldestCreatedDate() * 1000) +
                                " 更新时间:" + sdf.format(pr.getUpdatedDatelong() * 1000) +
                                " 修改评审人时间:" + sdf.format(pr.getLastestAddOrReMoveReviewerTime() * 1000)
                );

                for (String branchName : branchNames) {
                    if (displayId.toLowerCase().contains(branchName)) {
                        isTargetBranch = true;
                    }
                }

                //单测阶段
                if (isTargetBranch && pr.getState().equals("OPEN")
                        && ((currDate - pr.getUpdatedDatelong() <= 5 && (currDate - pr.getLastestAddOrReMoveReviewerTime() > 5))  //表示不是更新评审人操作
                        || (currDate - pr.getUpdatedDatelong() <= 5 && (pr.getLastestAddOrReMoveReviewerTime() - pr.getOldestCreatedDate() <= 5))) //表示提交pr
                        || isTriggers[0] || isTriggers[3]) {
                    System.out.println("isTargetBranch = "+isTargetBranch );
                    System.out.println("pr.getState().equals(\"OPEN\") = "+pr.getState().equals("OPEN") );
                    System.out.println("currDate - pr.getUpdatedDatelong() = "+(currDate - pr.getUpdatedDatelong()) );
                    System.out.println("currDate - pr.getLastestAddOrReMoveReviewerTime() = "+(currDate - pr.getLastestAddOrReMoveReviewerTime()) );
                    System.out.println("pr.getLastestAddOrReMoveReviewerTime() - pr.getOldestCreatedDate() = "+(pr.getLastestAddOrReMoveReviewerTime() - pr.getOldestCreatedDate()) );
                    System.out.println("是否是手动触发java单测 = "+isTriggers[0]);
                    System.out.println("是否是手动触发c++单测 = "+isTriggers[3]);

                    ArrayList<String> list = new ArrayList<>();
                    if(isTriggers[0])
                        list.add("java");
                    else if(isTriggers[3])
                        list.add("c++");
                    else
                        list.add("java");
                    pr.buildTask("unitTest", null, list.toArray(new String[list.size()]));
                    prids.add(pr);
                }

                //benchmark阶段,
                if (isTriggers[1] || isTriggers[2]) {
                    ArrayList<String> list = new ArrayList<>();
                    if (isTriggers[1]) list.add("normal");
                    //if (isTriggers[2]) list.add("dict");
                    pr.buildTask("benchmarkTest", list.toArray(new String[list.size()]), null);
                    prids.add(pr);
                }else if(isTriggers[4]){
                    ArrayList<String> list = new ArrayList<>();
                    list.add("normal");
                    pr.buildTask("benchmarkTestC", list.toArray(new String[list.size()]), null);
                    prids.add(pr);
                }

            }

            int prcount = prids.size();
            AtomicInteger oldPrCount = new AtomicInteger();
            BufferedReader reader = new BufferedReader(new FileReader(filepath));
            String oldPrId;
            while ((oldPrId = reader.readLine()) != null) {
                oldPrids.add(oldPrId);
            }
            reader.close();
            //如果旧文件中不存在数据，就将新文件中的数据放入到prids中
            if (oldPrids.size() == 0 && newprids.size() > 0) newprids.add(prids.get(0).getPrId());

            //如果旧表单中存在的数据，并且新表单中存在就将其加入到最终结果中
            oldPrids.forEach(oldPrid -> {
                int curcount = 0;
                oldPrCount.getAndIncrement();
                for (int i = 0; i < prids.size(); i++) {
                    //如果oldPrId存在，但是prid不存在就删除
                    if (oldPrid.equals(prids.get(i))) break;
                    else curcount++;
                }
                if (curcount != prcount) newprids.add(oldPrid);
            });
            for (PR pr : prids) {
                AtomicInteger curCount = new AtomicInteger();
                oldPrids.forEach(oldPrid -> {
                    try {
                        if (!pr.getPrId().equals(oldPrid)) curCount.getAndIncrement();
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                });
                if (curCount.get() == oldPrCount.get()) {
                    newprids.add(pr.getPrId());
                    todealPr = pr;
                    break;
                }
                else {
                    System.out.println("curCount.get() = "+curCount.get());
                    System.out.println("oldPrCount.get() = "+oldPrCount.get());
                }
            }
            StringBuffer resPr = new StringBuffer();
            FileWriter fw = new FileWriter(filepath);
            newprids.forEach(l -> {
                resPr.append(l + "\n");
            });
            fw.write(String.valueOf(resPr));
            fw.close();
        } catch (IOException e) {
            e.printStackTrace();
        } catch (Exception e) {
            e.printStackTrace();
        }
        System.out.println("Objects.isNull(todealPr) = " + Objects.isNull(todealPr));
        if (!Objects.isNull(todealPr)){
            System.out.println("todealPr = " + todealPr.getPrId());
        }
        return todealPr;
    }

    private static void persistCreateTaskAsync(PR pr) {
        Future<?> future = executorService.submit(() -> {
            try {
                persistCreateTask(pr);
            } catch (Exception e) {
                e.printStackTrace();
            }
        });
    }

    private static void persistCreateTask(PR pr) throws Exception {
        if(pr.getDisplayId().contains("persist")) {
            //先查询缓存如果缓存不存在，就判断数据库是否存在，如果不存在就创建任务
            persistTaskCache.forEach( task -> {
                try {
                    if(task.equals(pr.getPrId())){
                        return;
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            });

            List<Map<String, String>> result = DBUtils.query("select count(*) as count from persistTask where prid=\"" + pr.getPrId() + "\"", "count");
            if (Integer.parseInt(result.get(0).get("count")) > 0) {
                return;
            }else {
                //创建任务，并写入数据库，写入缓存
                JiraUtils jiraUtils = new JiraUtils();
                jiraUtils.createIssue(pr);
                persistTaskCache.add(pr.getPrId());
                JSYDBUtils.updateData("INSERT INTO persistTask (prid) VALUES (" + pr.getPrId() +  ");");
            }
        }
    }

    public static void timedExecute(String workPath, String storagePath) {
        //建立数据库连接
        try {
            Class.forName("com.mysql.jdbc.Driver");
            //查看分支
            List<String> brachNames = DBUtils.readBranchName();

            //定时执行
            Runnable runnable = new Runnable() {
                @Override
                public void run() {
                    try{
                        BitBucketUtils bitBucketUtils = new BitBucketUtils(storagePath);
                        PR pr = getPr(workPath + "PreTest", bitBucketUtils, brachNames);

                        if (pr != null) {

                            bitBucketUtils.downloadPatch(pr);

                            boolean isInsertCorrect = false;
                            System.out.println("触发的prid:" + pr.getPrId());

                            //检查是否是单元测试，如果是则记录当前执行时间并入库
                            if (pr.getTask().getTestType().equals("unitTest")) {
                                isInsertCorrect = JSYDBUtils.updateData("insert into jsyUnitTest (prId,executeTime) values (\"" + pr.getPrId() + "\"," + System.currentTimeMillis() + ");")>0;
                            }
                            else {
                                isInsertCorrect = true;
                            }
                            System.out.println("是否插入成功:"+isInsertCorrect);

                            if (isInsertCorrect){
                                if(pr.getTask().getDataTypes() != null) {
                                    for (String data : pr.getTask().getDataTypes()) System.out.println("数据类型:" + data);
                                }
                                JenkinsUtils jenkinsUtils = new JenkinsUtils(pr, workPath);

                                //返回当前分支的排队情况
                                jenkinsUtils.getQueuesNumber(pr ,bitBucketUtils.getCookie());

                                //触发对应的任务执行
                                jenkinsUtils.buildJenkinsBuild();
                            }

                        }
                    }
                    catch (Exception e){
                        e.printStackTrace();
                    }

                }
            };
            ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();
            scheduler.scheduleAtFixedRate(runnable, 0, 5, TimeUnit.SECONDS);
        } catch (ClassNotFoundException e) {
            e.printStackTrace();
        }
    }


    public static void main(String[] args) {
        String workPath = args[0];
        String storagePath = args[1] + "Patch/";
        timedExecute(workPath, storagePath);
    }
}
