package ci.benchMark;

import java.util.Objects;

/**
 * @author sunmuchao
 * @date 2023/10/8 4:15 下午
 */
public class TestResult {
    private String uuid;
    private String className;
    private double time;
    public TestResult(String className,Float time) {
        this.className = className;
        this.time = time;
    }

    public String getUuid() {
        return uuid;
    }

    public String getClassName() {
        return className;
    }



    public double getTime() {
        return time;
    }

    public void setUuid(String uuid) {
        this.uuid = uuid;
    }

    public void setClassName(String className) {
        this.className = className;
    }

    public void setTime(double time) {
        this.time += time;
    }

    @Override
    public boolean equals(Object obj) {
    TestResult that = (TestResult) obj;
        return Objects.equals(className, that.className);
    }

    @Override
    public int hashCode() {
        return Objects.hash(className);
    }
}
