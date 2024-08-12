package ci.benchMark;

/**
 * @author sunmuchao
 * @date 2024/4/28 9:50 上午
 */

//比较结果元器件：用于填充单一用例的对比结果信息
public class BenchmarkResultComponent {
    private String caseName;
    //用于填充结果字段信息的
    private BenchmarkResultItem A;
    private BenchmarkResultItem B;
    //A相对于B是否性能上升
    public Boolean PerformanceRise;
    //A相对于B是否性能下降
    public Boolean PerformanceReduce;
    //A是否是失败用例
    public Boolean fail;
    //A是否是新增用例
    public Boolean isNewAdded;

    BenchmarkResultComponent(String caseName, BenchmarkResultItem A, BenchmarkResultItem B){
        this.caseName = caseName;
        this.A = A;
        this.B = B;
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

    public void setA(BenchmarkResultItem a) {
        A = a;
    }

    public BenchmarkResultItem getB() {
        return B;
    }

    public void setB(BenchmarkResultItem b) {
        B = b;
    }

    public void isNewAdded(Boolean isNewAdded) {
        this.isNewAdded = isNewAdded;
    }

    @Override
    public boolean equals(Object obj) {
        // 检查是否是同一个对象
        if (this == obj) {
            return true;
        }

        // 检查是否为null或者是否是不同的类
        if (obj == null || getClass() != obj.getClass()) {
            return false;
        }

        // 将obj转换为BenchmarkResultComponent并比较caseName
        BenchmarkResultComponent that = (BenchmarkResultComponent) obj;
        return caseName != null ? (caseName.equals(that.caseName) &&
                (this.PerformanceReduce != null && that.PerformanceReduce != null) ||
                (this.PerformanceRise != null && that.PerformanceRise != null) ||
                (this.fail != null && that.fail != null)
        ) : that.caseName == null;
    }

    // 重写hashCode方法
    @Override
    public int hashCode() {
        return caseName != null ? caseName.hashCode() : 0;
    }

    // 示例中的toString方法，可以根据需要调整
    @Override
    public String toString() {
        return "BenchmarkResultComponent{" +
                "caseName='" + caseName + '\'' +
                '}';
    }
}
