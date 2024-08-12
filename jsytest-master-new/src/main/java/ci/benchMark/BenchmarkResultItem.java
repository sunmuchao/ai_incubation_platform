package ci.benchMark;

/**
 * @author sunmuchao
 * @date 2024/4/28 11:54 上午
 */
//用于填充结果字段信息的
public class BenchmarkResultItem {
    private String prid;
    private int measureTime;
    private String ErrorInfo;

    public String getPrid() {
        return prid;
    }

    public BenchmarkResultItem setPrid(String prid) {
        this.prid = prid;
        return this;
    }

    public int getMeasureTime() {
        return measureTime;
    }

    public BenchmarkResultItem setMeasureTime(int measureTime) {
        this.measureTime = measureTime;
        return this;
    }

    public String getErrorInfo() {
        return ErrorInfo;
    }

    public BenchmarkResultItem setErrorInfo(String errorInfo) {
        ErrorInfo = errorInfo;
        return this;
    }

    public Object acquireGetField(String fieldName){
        if(fieldName.equals("prid")){
            return getPrid();
        }else if(fieldName.equals("measureTime")){
            return getMeasureTime();
        }else if(fieldName.equals("ErrorInfo")){
            return getErrorInfo();
        }
        return null;
    }
}
