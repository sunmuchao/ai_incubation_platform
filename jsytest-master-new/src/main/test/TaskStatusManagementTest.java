import ci.benchMark.TaskStatusManagement;
import org.junit.Assert;
import org.junit.Test;

/**
 * @author sunmuchao
 * @date 2024/8/1 3:10 下午
 */
public class TaskStatusManagementTest {

    @Test
    public void testTaskDuplicateSubmission1(){
        TaskStatusManagement tsm1 = new TaskStatusManagement("111", "1");
        tsm1.createTaskInformation();
        TaskStatusManagement tsm2 = new TaskStatusManagement("222", "1");
        tsm2.createTaskInformation();
        Assert.assertTrue(tsm1.isHasNewerRecurringTask());
    }

    @Test
    public void testTaskDuplicateSubmission2(){
        TaskStatusManagement tsm1 = new TaskStatusManagement("111", "1");
        tsm1.createTaskInformation();
        TaskStatusManagement tsm2 = new TaskStatusManagement("222", "1");
        tsm2.createTaskInformation();
        tsm2.modifyStatus2Finish();

        Assert.assertFalse(tsm1.isHasNewerRecurringTask());

    }

    @Test
    public void testTaskDuplicateSubmission3(){
        TaskStatusManagement tsm1 = new TaskStatusManagement("111", "1");
        tsm1.createTaskInformation();
        TaskStatusManagement tsm2 = new TaskStatusManagement("222", "1");
        tsm2.createTaskInformation();
        tsm2.createTaskInformation();
        tsm2.modifyStatus2Cancel();

        Assert.assertFalse(tsm1.isHasNewerRecurringTask());
    }


}
