package ci.benchMark;

import java.util.List;

/**
 * @author sunmuchao
 * @date 2023/9/27 3:42 下午
 */
public class TestResultsTaskRelationship {
    private String jobName;
    private List<TestResult> testResults;
    private double totalTime;
    private String taskName;

    public TestResultsTaskRelationship(List<TestResult> testResults){
        this.testResults = testResults;
    }

    public String getJobName() {
        return jobName;
    }

    public void setJobName(String jobName) {
        this.jobName = jobName;
    }

    public double getTotalTime(){
        totalTime = 0;
        for(TestResult testResult : testResults){
            totalTime += testResult.getTime();
        }
        return totalTime;
    }

    public String getClassNameStr(){
        StringBuffer sb = new StringBuffer();
        for(TestResult testResult : testResults){
            sb.append(testResult.getClassName() + "\n");
        }
        return sb.toString();
    }

    public String getTaskName() {
        return taskName;
    }

    public void setTaskName(String taskName) {
        this.taskName = taskName;
    }
}
