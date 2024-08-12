package ci.benchMark;

import java.util.Objects;

/**
 * @author sunmuchao
 * @date 2023/10/8 4:15 下午
 */
public class JobTask {
    private String name;
    private double time;
    public JobTask(String name,Float time) {
        this.name = name;
        this.time = time;
    }


    public double getTime() {
        return time;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    @Override
    public boolean equals(Object obj) {
        JobTask that = (JobTask) obj;
        return Objects.equals(name, that.name);
    }

    @Override
    public int hashCode() {
        return Objects.hash(name);
    }
}
