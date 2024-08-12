package ci.benchMark;

import com.alibaba.fastjson.JSONObject;

import java.io.IOException;
import java.io.OutputStream;
import java.io.OutputStreamWriter;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLConnection;

public class AddComment {

    public static void addComment(String prId, String rememberMe, String branch, String failures, String failReport, String consoleReport, String testNumber) {
        try {
            String url = "https://code.fineres.com/rest/api/latest/projects/CAL/repos/polars/pull-requests/" + prId + "/comments?diffType=EFFECTIVE&markup=true&avatarSize=48";
            HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
            connection.setRequestProperty("Cookie", rememberMe);
            connection.setRequestMethod("POST");
            connection.setDoInput(true);
            connection.setDoOutput(true);
            connection.setRequestProperty("Referer", "https://code.fineres.com/projects/CAL/repos/polars/pull-requests/1742/overview");
            connection.setRequestProperty("Content-Type", "application/json");

            JSONObject json = new JSONObject();
            StringBuilder text = new StringBuilder();

            if (failures == null || failures.isEmpty() || "null".equals(failures)) {
                text.append("测试分支: ").append(branch)
                        .append("\n构建失败")
                        .append("\n请检查原因!!! 控制台日志: ").append(consoleReport);
            } else if (Integer.parseInt(failures) == 0) {
                if (branch.contains("11") || branch.contains("llvm")) {
                    text.append("测试分支: ").append(branch)
                            .append("\n测试通过")
                            .append("\n单测总数量: ").append(testNumber)
                            .append("\n单测报告: ").append(failReport);
                } else {
                    text.append("测试分支: ").append(branch)
                            .append("\n编译通过");
                }
            } else {
                text.append("测试分支: ").append(branch)
                        .append("\n测试失败数量: ").append(failures)
                        .append("\n单测总数量: ").append(testNumber)
                        .append("\n测试未通过 失败报告: ").append(failReport);
            }

            if ("polars_test_llvm".equals(branch)) {
                text.append("\nC++单测!!!");
            }

            json.put("text", text.toString());
            json.put("severity", "NORMAL");

            try (OutputStreamWriter writer = new OutputStreamWriter(connection.getOutputStream(), "UTF-8")) {
                writer.write(json.toString());
                writer.flush();
            }

            connection.connect();
            if (connection.getResponseCode() == HttpURLConnection.HTTP_CREATED) {
                System.out.println("请求正常");
            } else {
                System.out.println("请求失败");
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    private static void addBenchmarkComment(String prId, String rememberMe, String failures, String failReport, String fall, String up, String normalCount, String avgScore, String avgConScore, String report) {
        try {
            String url = "https://code.fineres.com/rest/api/latest/projects/CAL/repos/polars/pull-requests/" + prId + "/comments?diffType=EFFECTIVE&markup=true&avatarSize=48";
            HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
            connection.setRequestProperty("Cookie", rememberMe);
            connection.setRequestMethod("POST");
            connection.setDoInput(true);
            connection.setDoOutput(true);
            connection.setRequestProperty("Referer", "https://code.fineres.com/projects/CAL/repos/polars/pull-requests/1742/overview");
            connection.setRequestProperty("Content-Type", "application/json");

            JSONObject json = new JSONObject();
            StringBuilder text = new StringBuilder();

            if (failures != null && !"null".equals(failures)) {
                int newCaseCount = Integer.parseInt(failures);
                int errCaseCount = Integer.parseInt(failReport);
                String dataType = report.contains("normal") ? "normal" : report.contains("dict") ? "dict" : null;

                text.append("数据类型: ").append(dataType)
                        .append("\n新增: ").append(newCaseCount)
                        .append("\n错误: ").append(errCaseCount)
                        .append("\n性能下降: ").append(fall)
                        .append("\n性能上升: ").append(up)
                        .append("\n性能未变化: ").append(normalCount)
                        .append("\n单并发分值: ").append(avgScore)
                        .append("\n并发分值: ").append(avgConScore)
                        .append("\n结果报告: ").append(report);
            } else {
                text.append("benchmark执行失败请检查报告,@Sun.Sun排查问题");
            }

            json.put("text", text.toString());

            try (OutputStreamWriter writer = new OutputStreamWriter(connection.getOutputStream(), "UTF-8")) {
                writer.write(json.toString());
                writer.flush();
            }

            connection.connect();
            if (connection.getResponseCode() == HttpURLConnection.HTTP_CREATED) {
                System.out.println("请求正常");
            } else {
                System.out.println("请求失败");
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public static String getCookie() {
        String url = "https://code.fineres.com/j_atl_security_check";
        try {
            String param = "j_username=Sun.Sun&j_password=sunmuchao980320$$&_atl_remember_me=on&submit=登录&scan=企业微信扫码登录";
            HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
            connection.setInstanceFollowRedirects(false);
            connection.setDoOutput(true);
            connection.setDoInput(true);
            connection.setRequestMethod("POST");
            connection.setRequestProperty("Cookie", "_ga=GA1.2.145599097.1623144057; SPC-SELECTED-CATEGORY-CORE=all; SPC-SELECTED-CATEGORY=18; BITBUCKETSESSIONID=34C6CC0F403F81E0228EC169B4904E4D");

            try (OutputStream os = connection.getOutputStream()) {
                os.write(param.getBytes());
            }

            return connection.getHeaderField("Set-Cookie").split(";")[0];
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    public static void main(String[] args) {
        String prId = args[0];
        String branch = args[1];
        String failures = args[2];
        String UnitTestReport = args[3];
        String consoleReport = args[4];
        String testNumber = args[5];
        String rememberMe = getCookie();

        addComment(prId, rememberMe, branch, failures, UnitTestReport, consoleReport, testNumber);

        // Uncomment the following block if you need to add benchmark comments
        /*
        if ("polars_test-benchmark".equals(branch)) {
            String fall = args[5];
            String up = args[6];
            String normalCount = args[7];
            String avgScore = args[8];
            String avgConScore = args[9];
            String report = args[10];
            addBenchmarkComment(prId, rememberMe, failures, failReport, fall, up, normalCount, avgScore, avgConScore, report);
        }
        */
    }
}
