package polarsPerformance;

import java.util.ArrayList;

public class JsySqlPerformance {
    private String caseName;
    private String traceId;
    private ArrayList<String> taskNames;
    private int runTime;
    private int executionAllTime;
    private String curTime;
    private int responseTime;

    public JsySqlPerformance() {
    }

    public JsySqlPerformance(Builder builder){
        this.caseName = builder.caseName;
        this.traceId = builder.traceId;
        this.taskNames = builder.taskNames;
        this.runTime = builder.runTime;
        this.executionAllTime = builder.executionAllTime;
        this.curTime = builder.curTime;
        this.responseTime=builder.responseTime;

    }


    public String getCaseName() {
        return caseName;
    }

    public void setCaseName(String caseName) {
        this.caseName = caseName;
    }

    public String getTraceId() {
        return traceId;
    }

    public void setTraceId(String traceId) {
        this.traceId = traceId;
    }

    public ArrayList<String> getTaskNames() {
        return taskNames;
    }

    public void setTaskNames(ArrayList<String> taskNames) {
        this.taskNames = taskNames;
    }

    public int getRunTime() {
        return runTime;
    }

    public void setRunTime(int runTime) {
        this.runTime = runTime;
    }

    public int getExecutionAllTime() {
        return executionAllTime;
    }

    public void setExecutionAllTime(int executionAllTime) {
        this.executionAllTime = executionAllTime;
    }

    public String getCurTime() {
        return curTime;
    }

    public void setCurTime(String curTime) {
        this.curTime = curTime;
    }

    public int getResponseTime() {
        return responseTime;
    }

    public void setResponseTime(int responseTime) {
        this.responseTime = responseTime;
    }

    public static class Builder{
        private String caseName;
        private String traceId;
        private ArrayList<String> taskNames;
        private int runTime;
        private int executionAllTime;
        private String curTime;
        private int responseTime;

        public Builder() {}

        public Builder setCaseName(String caseName) {
            this.caseName = caseName;
            return this;
        }

        public Builder setTraceId(String traceId) {
            this.traceId = traceId;
            return this;
        }

        public Builder setTaskNames(ArrayList<String> taskNames) {
            this.taskNames = taskNames;
            return this;
        }

        public Builder setRunTime(int runTime) {
            this.runTime = runTime;
            return this;
        }

        public Builder setExecutionAllTime(int executionAllTime) {
            this.executionAllTime = executionAllTime;
            return this;
        }

        public Builder setCurTime(String curTime) {
            this.curTime = curTime;
            return this;
        }

        public Builder setResponseTime(int responseTime) {
            this.responseTime = responseTime;
            return this;
        }

        public JsySqlPerformance build(){
            return new JsySqlPerformance(this);

        }

    }



}
