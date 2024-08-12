package buriedPoint.executor;

import java.util.ArrayList;

public class Executor {
    private int queueTime;
    public ArrayList<String> childIds;
    private String metric;
    private String pls;
    private String suite;
    private int realPolarsTime;
    private int clos;
    private int stepNumber;
    private int opentime;
    private int maxRows;
    public boolean isProblem = true;

    public int getClos() {
        return clos;
    }

    public void setClos(int clos) {
        this.clos = clos;
    }

    public void setOpenTime(int opentime){
        this.opentime = opentime * 1000;
    }
    public int getOpenTime(){
        return opentime;
    }

    public int getQueueTime() {
        return queueTime;
    }

    public void setQueueTime(int queueTime) {
        this.queueTime = queueTime;
    }

    public int getRealPolarsTime() {
        return realPolarsTime;
    }

    public void setRealPolarsTime(int realPolarsTime) {
        this.realPolarsTime = realPolarsTime * 1000;
    }

    public void addChildId(String childId){
        childIds.add(childId);
    }

    public String getMetric() {
        return metric;
    }

    public void setMetric(String metric) {
        this.metric = metric;
    }

    public String getPls() {
        return pls;
    }

    public void setPls(String pls) {
        this.pls = pls;
    }

    public String getSuite() {
        return suite;
    }

    public void setSuite(String suite) {
        this.suite = suite;
    }

    public void setStepNumber(int stepNumber) {
        this.stepNumber = stepNumber;
    }

    public int getStepNumber() {
        return stepNumber;
    }

    public void setMaxRows(int maxRows) {
        this.maxRows = maxRows;
    }

    public int getMaxRows() {
        return maxRows;
    }
}
