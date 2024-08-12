package ci.benchMark;

import base.db.JSYDBUtils;

/**
 * @author sunmuchao
 * @date 2024/6/20 10:43 上午
 */
public class TaskStatusManagement {
    private String uuid;
    private String prId;

    //任务状态分为：begin 、finish 、cancel
    //begin: 在任务开始的时候
    //finish: 在reduce执行结束的时候
    //cancel: 情况1:当该任务的uuid的begin_time < 任务2的uuid的begin_time, 并且任务2的uuid的status不是finish，则将任务1置为cancel
    public TaskStatusManagement(String uuid, String prId) {
        this.uuid = uuid;
        this.prId = prId;
    }

    public void process(String taskStatus) {
        if ("begin".equals(taskStatus)) {
            createTaskInformation();
        } else if ("finish".equals(taskStatus)) {
            modifyStatus2Finish();
        } else if ("cancel".equals(taskStatus)) {
            cancelTask();
        }
    }

    public void modifyStatus2Cancel() {
        long cancelTime = System.currentTimeMillis();
        String sql = "update CI_Task_Information set task_status = \"cancel\", cancel_time = \"" + cancelTime + "\" where uuid = \"" + uuid + "\"";
        JSYDBUtils.updateData(sql);
    }

    public void modifyStatus2Finish() {
        long endTime = System.currentTimeMillis();
        String sql = "update CI_Task_Information set task_status = \"finish\", end_time = \"" + endTime + "\" where uuid = \"" + uuid + "\"";
        JSYDBUtils.updateData(sql);
    }

    public void createTaskInformation() {
        long beginTime = System.currentTimeMillis();
        String sql = "insert into CI_Task_Information(uuid, task_status, begin_time, prId) values " +
                "(\"" + uuid + "\",\"" + "begin\"," + beginTime + ",\"" + prId + "\")";
        JSYDBUtils.updateData(sql);
    }

    private void cancelTask() {
        modifyStatus2Cancel();
    }

    public boolean isHasNewerRecurringTask() {
        String sql = "select begin_time from CI_Task_Information where uuid=\"" + uuid + "\" and prId=\"" + prId + "\";";
        String begin_time = JSYDBUtils.query(sql);
        //查找select count(*) from CI_Task_Information where begin_time > "begin1_time" and prId=\"" + prId + "\" and status = "begin";
        String sql1 = "select count(*) from CI_Task_Information where begin_time > " + begin_time + " and prId = \"" + prId + "\" and task_status = \"begin\";";
        int count = Integer.parseInt(JSYDBUtils.query(sql1));
        if (count > 0) {
            //则取消当前任务
            return true;
        }
        return false;
    }
}
