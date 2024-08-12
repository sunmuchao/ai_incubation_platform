package ci.benchMark;

import java.util.ArrayList;
import java.util.List;

/**
 * @author sunmuchao
 * @date 2024/4/29 7:03 下午
 */
//用于填充单一用例的多个对比结果
public class BenchmarkResultComponent2 {
    private String caseName;
    //用于填充结果字段信息的
    private BenchmarkResultItem A;
    private List<BenchmarkResultItem> B;
    //A相对于B是否性能上升
    public Boolean PerformanceRise;
    //A相对于B是否性能下降
    public Boolean PerformanceReduce;
    //A是否是失败用例
    public Boolean fail;

    BenchmarkResultComponent2(String caseName){
        this.caseName = caseName;
        B = new ArrayList<>();
    }

    public void setA(BenchmarkResultItem a){
        if(A == null) {
            A = a;
        }
    }


    public void addBenchmarkResultItemToB(BenchmarkResultItem b){
        B.add(b);
    }

    public List<BenchmarkResultItem> getB(){
        return B;
    }

    public String getCaseName(){
        return caseName;
    }

    public void isPerformanceRise(Boolean b){
        this.PerformanceRise = b;
    }

    public void isPerformanceReduce(Boolean b){
        this.PerformanceReduce = b;
    }

    public void isFail(Boolean b){
        this.fail = b;
    }

    public BenchmarkResultItem getA() {
        return A;
    }
}
