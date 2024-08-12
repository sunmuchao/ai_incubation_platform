package ci.benchMark;

import java.util.LinkedList;
import java.util.Queue;

/**
 * @author sunmuchao
 * @date 2024/4/26 10:46 上午
 */
//表单:用于填充比较集合的
public class BenchmarkForm {

    private PR curPr;
    private Queue<PR> prQueue;

    public BenchmarkForm setPrQueue(Queue<PR> prQueue1){
        //队列进行拷贝，不直接使用
        prQueue = new LinkedList<>();
        prQueue.addAll(prQueue1);
        return this;
    }

    public Queue<PR> getPrQueue(){
        return prQueue;
    }

    public PR getCurPr() {
        return curPr;
    }

    public BenchmarkForm setCurPr(PR curPr) {
        this.curPr = curPr;
        return this;
    }
}
