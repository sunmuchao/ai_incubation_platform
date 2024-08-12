package polarsPerformance;

import java.util.ArrayList;

public class jsyPerformance {
    public ArrayList<Case> cases;
    jsyPerformance(){
        cases = new ArrayList<>();
    }
    public void addCase(Case c){
        cases.add(c);
    }
}
class Case {
    private String traceId;
    private String caseName;
    private ArrayList<String> taskNames;

    Case(String traceId, String caseName){
        this.traceId = traceId;
        this.caseName = caseName;
        taskNames = new ArrayList<String>();
    }

    public String getTraceId() {
        return traceId;
    }

    public String getCaseName() {
        return caseName;
    }

    public ArrayList<String> getTaskNames() {
        return taskNames;
    }

    public void setTaskName(String taskName) {
        if(taskName != null && !taskName.equals("null")) {
            System.out.println("taskName:" + taskName);
            taskNames.add(taskName);
        }
    }
}