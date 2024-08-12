package polarsPerformance;

import lombok.Builder;
import lombok.Getter;
import lombok.Setter;


@Builder
@Getter
@Setter
public class JsySqlPerformanceForNew {
    private String id;
    private String taskName;
    private String caseName;
    private String traceId;
    private String date;
    private String status;
    private String type;
    private String createTime;
    private String endTime;
    private String responseTime;
    private String queueTime;
    private String waitResourceTime;
    private String planTime;
    private String startTime;
    private String runTime;
    private String finishTime;
    private String executionAllTime;
    private String memPeak;
    private String memCurrent;
    private String workNode;
    private String metricDownloadPath;
    private String traceDownloadPath;
    private String suiteDownloadPath;
    private String isSuccessful;
    private String currentTime;

    @Override
    public String toString() {
        return "JsySqlPerformanceForNew{" +
                "id='" + id + '\'' +
                ", taskName='" + taskName + '\'' +
                ", caseName='" + caseName + '\'' +
                ", traceId='" + traceId + '\'' +
                ", date='" + date + '\'' +
                ", status='" + status + '\'' +
                ", type='" + type + '\'' +
                ", createTime='" + createTime + '\'' +
                ", endTime='" + endTime + '\'' +
                ", responseTime='" + responseTime + '\'' +
                ", queueTime='" + queueTime + '\'' +
                ", waitResourceTime='" + waitResourceTime + '\'' +
                ", planTime='" + planTime + '\'' +
                ", startTime='" + startTime + '\'' +
                ", runTime='" + runTime + '\'' +
                ", finishTime='" + finishTime + '\'' +
                ", executionAllTime='" + executionAllTime + '\'' +
                ", memPeak='" + memPeak + '\'' +
                ", memCurrent='" + memCurrent + '\'' +
                ", workNode='" + workNode + '\'' +
                ", metricDownloadPath='" + metricDownloadPath + '\'' +
                ", traceDownloadPath='" + traceDownloadPath + '\'' +
                ", suiteDownloadPath='" + suiteDownloadPath + '\'' +
                ", isSuccessful='" + isSuccessful + '\'' +
                '}';
    }
}
