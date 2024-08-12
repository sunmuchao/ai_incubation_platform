package base.third.jira;

import buriedPoint.DBUtils;
import buriedPoint.point.BuriedPoint;
import ci.benchMark.PR;
import com.atlassian.jira.rest.client.api.JiraRestClient;
import com.atlassian.jira.rest.client.api.domain.BasicIssue;
import com.atlassian.jira.rest.client.api.domain.Issue;
import com.atlassian.jira.rest.client.api.domain.IssueFieldId;
import com.atlassian.jira.rest.client.api.domain.input.ComplexIssueInputFieldValue;
import com.atlassian.jira.rest.client.api.domain.input.FieldInput;
import com.atlassian.jira.rest.client.api.domain.input.IssueInput;
import com.atlassian.jira.rest.client.api.domain.input.IssueInputBuilder;
import com.atlassian.jira.rest.client.internal.async.AsynchronousJiraRestClientFactory;
import com.google.common.base.Function;
import com.google.common.collect.Iterables;
import io.atlassian.util.concurrent.Promise;
import org.checkerframework.checker.nullness.qual.Nullable;

import java.io.IOException;
import java.net.URI;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.text.DecimalFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.ExecutionException;

public class JiraUtils {
    static String affectsVersion = "JSY-3.5.4+";
    private JiraRestClient restClient = null;

    private DBUtils dbUtils;

    public JiraUtils(DBUtils dbUtils) {
        restClient = loginJira("https://work.fineres.com/", "Sun.Sun", "SunMuChao3!!");
        this.dbUtils = dbUtils;
    }

    public JiraUtils() {
        restClient = loginJira("https://work.fineres.com/", "Sun.Sun", "sunmuchao980320$$");
    }

    public void createIssue(PR pr) throws IOException {
        try {
            BasicIssue issue = null;
            IssueInputBuilder builder = new IssueInputBuilder();
            builder.setIssueTypeId((long) 10410);
            builder.setProjectKey("KERNEL");
            builder.setSummary("@" + pr.getBuilder() + " 检查prid=" + pr.getPrId() + "的代码是否有提交stable分支");
            builder.setDescription("请检查https://code.fineres.com/projects/CAL/repos/polars/pull-requests/" + pr.getPrId() +  "/overview 提交是否需要提交stable分支等, 需检查：1.相对应产品线的stable分支是否有提交 2.该bug如果在其他产品线也会出现是否也需要在其他产品线的stable分支提交，提交合并后转验收");
            builder.setFieldValue("labels", Arrays.asList("漏提交问题"));
            IssueInput issueInput = builder.build();
            issue = restClient.getIssueClient().createIssue(issueInput).claim();
            System.out.println("url:" + issue.getSelf());
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            restClient.close();
        }
    }


    public JiraRestClient getRestClient() {
        return restClient;
    }

    public String createIssue(BuriedPoint buriedPoint, String traceid, String description) throws IOException {
        BasicIssue issue = null;
        float totoalTimefloat = buriedPoint.getTotalTime();
        IssueInputBuilder builder = new IssueInputBuilder();
        builder.setIssueTypeId((long) 10400);
        builder.setProjectKey("JSY");
        String totoalTimestring = new DecimalFormat("#.0").format(totoalTimefloat);
        double totoalTime = Double.parseDouble(totoalTimestring);
        if (buriedPoint.getClass().getName().contains("UpdateBuriedPoint")) {
            if (buriedPoint.getTableName() != null) {
                builder.setSummary("【更新】引擎-" + buriedPoint.getTableName() + "-" + traceid + "-" + totoalTime + "s");
                System.out.println("【更新】引擎-" + buriedPoint.getTableName() + "-" + traceid + "-" + totoalTime + "s");
            }
        } else {
            if (buriedPoint.getTableName() != null) {
                builder.setSummary("引擎-" + buriedPoint.getTableName() + "-" + buriedPoint.getSense() + "-" + buriedPoint.getOperatorType() + "-" + traceid + "-" + totoalTime + "s");
                System.out.println("引擎-" + buriedPoint.getTableName() + "-" + buriedPoint.getSense() + "-" + buriedPoint.getOperatorType() + "-" + traceid + "-" + totoalTime + "s");
            } else {
                builder.setSummary("引擎-" + buriedPoint.getWidgetName() + "-" + buriedPoint.getSense() + "-" + buriedPoint.getWidgetType() + "-" + traceid + "-" + totoalTime + "s");
                System.out.println("引擎-" + buriedPoint.getWidgetName() + "-" + buriedPoint.getSense() + "-" + buriedPoint.getWidgetType() + "-" + traceid + "-" + totoalTime + "s");
            }
        }
        System.out.println("description:" + description);
        builder.setDescription(description);
        if (totoalTimefloat >= 20)
            builder.setFieldInput(new FieldInput(IssueFieldId.PRIORITY_FIELD, ComplexIssueInputFieldValue.with("name", "非常紧急")));
        else if (totoalTimefloat >= 10)
            builder.setFieldInput(new FieldInput(IssueFieldId.PRIORITY_FIELD, ComplexIssueInputFieldValue.with("name", "紧急")));
        else
            builder.setFieldInput(new FieldInput(IssueFieldId.PRIORITY_FIELD, ComplexIssueInputFieldValue.with("name", "一般紧急")));
        List affectsVersions = new ArrayList();
        List components = new ArrayList();
        affectsVersions.add(affectsVersion);
        components.add("后端-性能");
        builder.setFieldInput(new FieldInput(IssueFieldId.AFFECTS_VERSIONS_FIELD, toListOfComplexIssueInputFieldValueWithSingleKey(affectsVersions, "name")));
        builder.setFieldInput(new FieldInput(IssueFieldId.COMPONENTS_FIELD, toListOfComplexIssueInputFieldValueWithSingleKey(components, "name")));
        IssueInput issueInput = builder.build();
        try {
            issue = restClient.getIssueClient().createIssue(issueInput).claim();
            System.out.println("url:" + issue.getSelf());
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            restClient.close();
        }
        return issue.getKey();
    }

    public static <T> Iterable<ComplexIssueInputFieldValue> toListOfComplexIssueInputFieldValueWithSingleKey(final Iterable<T> items, final String key) {
        return Iterables.transform(items, new Function<T, ComplexIssueInputFieldValue>() {
            @Override
            public @Nullable ComplexIssueInputFieldValue apply(@Nullable T value) {
                return ComplexIssueInputFieldValue.with(key, value);
            }
        });
    }

    private static JiraRestClient loginJira(String url, String userName, String pwd) {
        AsynchronousJiraRestClientFactory asynchronousJiraRestClientFactory = new AsynchronousJiraRestClientFactory();
        JiraRestClient jiraRestClient = asynchronousJiraRestClientFactory.createWithBasicHttpAuthentication(URI.create(url), userName, pwd);
        return jiraRestClient;
    }

    public boolean isnotNewProblem(String reason, BuriedPoint buriedPoint) throws SQLException, ExecutionException, InterruptedException {
        String tableName;
        if (buriedPoint.getClass().getName().contains("UpdateBuriedPoint")) tableName = "jsyUpdate";
        else tableName = "jsy";

        boolean isBug = false;
        //先判斷之前的bug是否被處理掉，如果沒有處理掉的話就過濾
        //如果處理掉的話，就重新提交
        ResultSet rs = dbUtils.SelectData("select trace from " + tableName + " where reason=\"" + reason + "\"");
        System.out.println("select trace from " + tableName + " where reason=\"" + reason + "\"");
        //如果没有值的话，则认为是bug
        if (rs.next()) {
            String trace = rs.getString(1);
            if (trace != null) {
                Promise<Issue> issues = (Promise<Issue>) getRestClient().getIssueClient().getIssue(trace);
                String status = issues.get().getStatus().toString();
                if (//status.contains("创建者确认") ||
                    //    status.contains("被否决") ||
                        status.contains("创建者验收") ||
                                status.contains("测试组员测试验收中") ||
                                status.contains("已解决")
                ) isBug = true;
            }
            while (rs.next()) {
                trace = rs.getString(1);
                if (trace != null) {
                    Promise<Issue> issues = (Promise<Issue>) getRestClient().getIssueClient().getIssue(trace);
                    String status = issues.get().getStatus().toString();
                    if (//status.contains("创建者确认") ||
                        //    status.contains("被否决") ||
                            status.contains("创建者验收") ||
                                    status.contains("测试组员测试验收中") ||
                                    status.contains("已解决")
                    ) isBug = true;
                }
            }
        } else isBug = true;

        if (isBug) {
            buriedPoint.addReason(reason);
            return false;
        } else {
            dbUtils.resIntoDB(buriedPoint.getTraceid(), reason, 0, tableName);
            return true;
        }
    }
}
