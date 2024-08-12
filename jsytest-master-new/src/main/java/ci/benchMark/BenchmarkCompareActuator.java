package ci.benchMark;

import ci.benchMark.comparator.BenchmarkPRComparator;
import java.util.LinkedList;
import java.util.Queue;

/**
 * @author sunmuchao
 * @date 2024/4/26 10:19 上午
 */

//比较执行器：完成单一用例的所有组合动作
public class BenchmarkCompareActuator {
    private String caseName;
    public BenchmarkCompareActuator(String caseName) {
        this.caseName = caseName;
    }

    public void performanceChanges(BenchmarkForm bf) throws Exception {
        //完成性能下降、性能上升、失败的场景判断
        //跟历史PR进行比较,比较标准: 性能提升的标准是跟三个历史pr比较均有提升，性能下降的标准是跟最近的一份历史pr进行比较性能下降
        Queue<PR> prQueue = bf.getPrQueue();
        Queue<PR> prQueue1 = new LinkedList<>();
        prQueue1.addAll(prQueue);

        //benchmark比较器
        BenchmarkPRComparator bc = new BenchmarkPRComparator(caseName);

        //性能上升判断
        PR curPR = bf.getCurPr();
        while(!prQueue.isEmpty()){
            PR oldPR = prQueue.poll();
            String curPrId = curPR.getPrId();
            String oldPrId = oldPR.getPrId();
            bc.performanceRise(curPrId, oldPrId);
        }

        //性能下降判断
        PR curPR1 = bf.getCurPr();
        PR oldPR1 = prQueue1.poll();
        String curPrId1 = curPR1.getPrId();
        String oldPrId1 = oldPR1.getPrId();
        bc.performanceReduce(curPrId1, oldPrId1);

        //失败的用例
        bc.performancefail(curPrId1);

        //新增的用例:跟最近的一份pr进行比较得到的
        bc.addedCases(curPrId1,oldPrId1);
    }

    public void competitorContrast(BenchmarkForm bf) {

    }
}
