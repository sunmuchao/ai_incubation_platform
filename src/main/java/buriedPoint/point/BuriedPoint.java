package buriedPoint.point;

import buriedPoint.executor.Executor;
import buriedPoint.executor.QueryExecutor;
//import org.apache.commons.lang3.StringUtils;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

public class BuriedPoint {
    private Float totalTime = null;
    private String duration = null;
    private String tableId = null;
    private String operatorType = null;
    private String sense = null;
    private String userName = null;
    private String tableName = null;
    private String startTime = null;
    private String endTime = null;
    private String widgetName = "";
    private String widgetType = "";
    private String jsyaddr = null;
    private long dateTimeTemp;
    private long totoalPolarsTime;
    public static List<Executor> Executors = null;
    private int ensuretablespacetime = 0;
    private int totalExecutetime = 0;

    private String traceid;

    private ArrayList<String> reasons = null;

    BuriedPoint(String traceid){
        Executors = new ArrayList<>();
        this.traceid = traceid;
        reasons = new ArrayList<>();
    }

    public String getTraceid() {
        return traceid;
    }

    public ArrayList<String> getReasons() {
        return reasons;
    }

    public void addReason(String reason) {
        reasons.add(reason);
    }

    SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");

    public float getTotalTime() {
        return totalTime;
    }

    public void setTotalTime(String duration) {
        this.duration = duration;
        this.totalTime = Float.parseFloat(duration) / 1000000;
    }

    public int getTotalExecutetime() {
        return totalExecutetime;
    }

    public void addTotalExecutetime(int totalExecutetime) {
        this.totalExecutetime += totalExecutetime;
    }

    public float getTotoalPolarsTime() {
        return (float) (totoalPolarsTime/1000000.0);
    }

    public void setTotoalPolarsTime(long polarsTime) {
        totoalPolarsTime += polarsTime;
    }


    public void addExecutor(Executor executor) {
        Executors.add(executor);
    }

    public String getTableId() {
        return tableId;
    }

    public void setTableId(String tableId) {
        if (tableId != null)
            this.tableId = tableId;
    }

    public String getOperatorType() {
        return operatorType;
    }

    public void setOperatorType(String operatorType) {
        if (operatorType != null) {
            if (operatorType.equals("Sort")) {
                operatorType = "排序";
            } else if (operatorType.equals("SelectFeild")) {
                operatorType = "选字段";
            } else if (operatorType.equals("RenameField")) {
                operatorType = "排序";
            } else if (operatorType.equals("Group")) {
                operatorType = "分组汇总";
            } else if (operatorType.equals("Join")) {
                operatorType = "左右合并";
            } else if (operatorType.equals("Column2Row")) {
                operatorType = "行转列";
            } else if (operatorType.equals("Row2Column")) {
                operatorType = "列转行";
            } else if (operatorType.equals("DeleteField")) {
                operatorType = "删除字段";
            } else if (operatorType.equals("ChangeFieldType")) {
                operatorType = "字段类型转换";
            } else if (operatorType.equals("Union")) {
                operatorType = "上下合并";
            } else if (operatorType.equals("AddNewColumn")) {
                operatorType = "新增列";
            } else if (operatorType.equals("FilterOperator")) {
                operatorType = "筛选";
            }
        }
        this.operatorType = operatorType;
    }

    public String getSense() {
        return sense;
    }

    public void setSense(String sense) {
        if (sense.equals("home")) {
            sense = "基础界面";
        } else if (sense.equals("analysis")) {
            sense = "分析表";
        } else if (sense.equals("chart")) {
            sense = "图表";
        } else if (sense.equals("dashboard")) {
            sense = "仪表板";
        }
        this.sense = sense;
    }

    public String getUserName() {
        return userName;
    }

    public void setUserName(String userName) {
        if (userName != null)
            this.userName = userName;
    }

    public String getTableName() {
        return tableName;
    }

    public void setTableName(String tableName) {
        if (tableName != null)
            this.tableName = tableName;
    }

    public String getStartTime() {
        return startTime;
    }


    public void setStartTime(String dateTime) {
        dateTimeTemp = Long.parseLong(dateTime.substring(0, dateTime.length() - 3));
        startTime = sdf.format(new Date(Long.parseLong(String.valueOf(dateTimeTemp))));
    }

    public void setUpdateStartTime(String dateTime) {
        dateTimeTemp = Long.parseLong(dateTime.substring(0, dateTime.length() - 6));
        startTime = sdf.format(new Date(Long.parseLong(String.valueOf(dateTimeTemp))));
    }

    public String getEndTime() {
        return endTime;
    }

    public void setEndTime(String endTime) {
        Date date = null;
        try {
            date = sdf.parse(startTime);
            date.setTime(dateTimeTemp + Integer.parseInt(duration) / 1000);
            endTime = sdf.format(date);
        } catch (ParseException e) {
            e.printStackTrace();
        }
    }

    public String getWidgetName() {
        return widgetName;
    }

    public void setWidgetName(String widgetName) {
        if (widgetName != null)
            this.widgetName = widgetName;
    }

    public String getWidgetType() {
        return widgetType;
    }

    public void setWidgetType(String widgetType) {
        if (widgetType != null)
            this.widgetType = widgetType;
    }

    public String getJsyaddr() {
        return jsyaddr;
    }

    public void setJsyaddr(String jsyaddr) {
        if (jsyaddr != null)
            this.jsyaddr = jsyaddr;
    }

    public int getEnsuretablespacetime() {
        return ensuretablespacetime;
    }

    public void addEnsuretablespacetime(int ensuretablespacetime) {
        this.ensuretablespacetime += ensuretablespacetime;
    }
}
