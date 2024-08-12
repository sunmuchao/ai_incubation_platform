import ci.benchMark.Scheduler;
import ci.benchMark.TestResult;
import ci.benchMark.TestResultsTaskRelationship;
import org.junit.Assert;
import org.junit.Test;

import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * @author sunmuchao
 * @date 2024/4/17 9:44 上午
 */
public class SchedulerTest {
    @Test
    public void testBindTaskToJob(){
        Map<String, Integer> selectedJobs = new HashMap<>();
        selectedJobs.put("CIUnitTestOperator1",9);
        selectedJobs.put("CIUnitTestOperator3",10);
        selectedJobs.put("CIUnitTestOperator7",6);
        selectedJobs.put("task1",1);
        selectedJobs.put("task2",1);
        selectedJobs.put("task3",1);
        selectedJobs.put("task4",1);
        selectedJobs.put("task5",1);

        List<TestResultsTaskRelationship> modules = new ArrayList<>();
        List<TestResult> testResults = new ArrayList<>();
        TestResultsTaskRelationship testResultsTaskRelationship1 = new TestResultsTaskRelationship(testResults);
        testResultsTaskRelationship1.setTaskName("task1");

        TestResultsTaskRelationship testResultsTaskRelationship2 = new TestResultsTaskRelationship(testResults);
        testResultsTaskRelationship2.setTaskName("task2");

        TestResultsTaskRelationship testResultsTaskRelationship3 = new TestResultsTaskRelationship(testResults);
        testResultsTaskRelationship3.setTaskName("task3");

        TestResultsTaskRelationship testResultsTaskRelationship4 = new TestResultsTaskRelationship(testResults);
        testResultsTaskRelationship4.setTaskName("task4");

        TestResultsTaskRelationship testResultsTaskRelationship5 = new TestResultsTaskRelationship(testResults);
        testResultsTaskRelationship5.setTaskName("task5");

        modules.add(testResultsTaskRelationship1);
        modules.add(testResultsTaskRelationship2);
        modules.add(testResultsTaskRelationship3);
        modules.add(testResultsTaskRelationship4);
        modules.add(testResultsTaskRelationship5);

        List<TestResultsTaskRelationship> modules1 = Scheduler.BindTaskToJob(selectedJobs,modules, 3);
        for (TestResultsTaskRelationship m : modules1){
            Assert.assertNotNull(m.getJobName());
        }
    }

    @Test
    public void testCopyProject() throws Exception {
        Path path = Paths.get("/Users/sunmuchao/Downloads/polars_5-16/");
        Scheduler.copyProject(path,"/Users/sunmuchao/Downloads/test/","11111");
    }

    @Test
    public void testTaskSplit() throws Exception {
        List<TestResult> result = null;
        int buildId = 2;
        String jobName = "test";
        Path projectPath = Paths.get("/Users/sunmuchao/Downloads/polars_ci/");
        Path workPath = projectPath;
        boolean isOnlyHihidataChange = false;
        result = Scheduler.addNewTestClass(Scheduler.getLastResult(result, buildId, jobName), projectPath, workPath);
        Assert.assertTrue(result.size() > 0);
    }
}
