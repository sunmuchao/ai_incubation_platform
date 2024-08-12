package base.third.bitBucket;

import base.third.wechat.WechatMessageUtils;
import ci.benchMark.PR;
import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import base.db.JSYDBUtils;
import okhttp3.FormBody;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okhttp3.ResponseBody;
import org.apache.commons.lang3.StringUtils;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLConnection;
import java.util.Arrays;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Properties;
import java.util.Queue;
import java.util.concurrent.*;

public class BitBucketUtils {
    private static String rememberme = null;
    private static String workPath;
    private String cookie;
    private String prId;
    private JSONObject response;
    private static final OkHttpClient client = new OkHttpClient().newBuilder()
            .readTimeout(60, TimeUnit.SECONDS)
            .connectTimeout(60, TimeUnit.SECONDS)
            .build();
    private static final OkHttpClient noFollowRedirectClient = new OkHttpClient().newBuilder()
            .readTimeout(60, TimeUnit.SECONDS)
            .connectTimeout(60, TimeUnit.SECONDS)
            .followRedirects(false)
            .build();
    private static final Long lastestAddOrReMoveReviewerTime = 0L;



    public BitBucketUtils(String prId){
        String url = "https://code.fineres.com/rest/api/latest/projects/CAL/repos/polars/pull-requests/" + prId;
        setCookie();
        JSONObject jsonObject =  JSON.parseObject(getResponse(url).toString());
        this.response = jsonObject;
    }

    public BitBucketUtils() {
        setCookie();
    }

    /**
     * 任意get请求*
     *
     * @param url url
     * @return 返回值
     */
    private String getGetResponse(String url) {
        Request request = new Request.Builder()
                .addHeader("Cookie", rememberme)
                .url(url)
                .build();
        Response response = null;
        try {
            response = client.newCall(request).execute();
            System.out.println("url=" + url);
            if (response.code() != 200) {
                return "";
            }
            System.out.println("response code= " + response.code());
            if (Objects.isNull(response.body())) {
                response.close();
                return "";
            } else {
                String body = Objects.requireNonNull(response.body()).string();
                response.close();
                return body;
            }
        } catch (IOException e) {
            System.out.println(e.getMessage());
            return "";
        } finally {
            if (Objects.nonNull(response))
                response.close();
        }
    }

    public StringBuffer getResponse(String url) {
        return new StringBuffer(getGetResponse(url));
    }


    /**
     * 获取token需要用logout获取session*
     *
     * @return sessionid
     */
    private String getSessionID() {
        Request request = new Request.Builder()
                .url("https://code.fineres.com/logout")
                .build();
        Response response = null;
        try {
            response = client.newCall(request).execute();
        } catch (IOException e) {
            e.printStackTrace();
        }
        String cookie = Objects.requireNonNull(response).header("Set-Cookie");
        response.close();
        if (StringUtils.isNotEmpty(cookie) && cookie.contains("BITBUCKETSESSIONID") && response.code() == 200) {
            return cookie.split("BITBUCKETSESSIONID=")[1].split(";")[0];
        }
        return null;
    }

    public void setCookie() {
        RequestBody requestBody = new FormBody.Builder()
                .add("j_username", "Sun.Sun")
                .add("j_password", "sunmuchao980320$$")
                .add("_atl_remember_me", "on")
                .add("submit", "登录")
                .add("scan", "企业微信扫码登录")
                .build();
        Request request = new Request.Builder()
                .url("https://code.fineres.com/j_atl_security_check")
                .addHeader("Cookie", "SPC-SELECTED-CATEGORY-pg2=all; SPC-SELECTED-CATEGORY-PG2=67; SPC-SELECTED-CATEGORY-JSY=all; SPC-SELECTED-CATEGORY-DEC=all; SPC-SELECTED-CATEGORY-BUSSINESS=all; _ga=GA1.2.145599097.1623144057; SPC-SELECTED-CATEGORY-CORE=all; SPC-SELECTED-CATEGORY=18; BITBUCKETSESSIONID=" + getSessionID())
                .post(requestBody)
                .build();
        Response response = null;
        try {
            response = noFollowRedirectClient.newCall(request).execute();
        } catch (IOException e) {
            e.printStackTrace();
        }
        cookie = Objects.requireNonNull(response).header("Set-Cookie");
        System.out.println(cookie);
        if (StringUtils.isNotEmpty(cookie) && cookie.contains("_atl_bitbucket_remember_me") && response.code() == 302) {
            rememberme = cookie.split(";")[0];
        }
        response.close();
    }

    public String getCookie() {
        return cookie;
    }


    public static void downloadPatch(PR pr) throws Exception {
        String prid = pr.getPrId();
        String url = "https://code.fineres.com/rest/patch/1.0/projects/CAL/repos/polars/pull-requests/" + prid + "/patch";
        Request request = new Request.Builder()
                .url(url)
                .addHeader("cookie", rememberme)
                .build();
        ResponseBody body = null;
        FileOutputStream fileOutputStream = null;
        BufferedReader bufferedReader = null;
        try {
            Response response = client.newCall(request).execute();
            body = response.body();
            bufferedReader = new BufferedReader(new InputStreamReader(body != null ? body.byteStream() : null));
            File file = new File(workPath + "polars-" + prid + ".patch");
            if (!file.exists()) file.createNewFile();
            fileOutputStream = new FileOutputStream(file);
            String line;
            while ((line = bufferedReader.readLine()) != null) {
                //是否是llvm代码
                if (line.contains("polars-llvm")) pr.setLLVM(true);
                line += "\n";
                fileOutputStream.write(line.getBytes());
            }
            pr.setIsOnlyHihidataChange(isOnlyHihidataChange(workPath + "polars-" + prid + ".patch"));
            pr.setIsContainBIChange(isContainBIChange(workPath + "polars-" + prid + ".patch"));
            pr.setIsContainHihidataChange(isContainHihidataChange(workPath + "polars-" + prid + ".patch"));


        } catch (IOException ioException) {
            ioException.printStackTrace();
        } finally {
            if (body != null) {
                body.close();
            }
            try {
                fileOutputStream.flush();
                fileOutputStream.close();
                bufferedReader.close();

            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }

    public static boolean isOnlyHihidataChange(String filePath) {
        Process process;
        try {
            String command = "grep \"diff --git\" " + filePath + " | " +
                    "awk -F\"/\" '{print $2}' && grep \"diff --git\" " + filePath + " | " +
                    "awk -F\"b/\" '{print $2}' | awk -F\"/\" '{print $1}'";
            System.out.println(command);
            process = Runtime.getRuntime().exec(new String[]{"/bin/sh", "-c", command});
            Thread waitForProcessThread = new Thread(() -> {
                try {
                    process.waitFor();
                } catch (InterruptedException e) {
                    // 进程被中断
                    e.printStackTrace();
                }
            });

            waitForProcessThread.start();
            long timeoutMillis = 60000; // 60秒
            waitForProcessThread.join(timeoutMillis);
            if (waitForProcessThread.isAlive()) {
                process.destroy();
                waitForProcessThread.interrupt();
                return false;
            }

            BufferedReader br = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;
            while ((line = br.readLine()) != null) {
                System.out.println(line);
                if (!line.equals("polars-hihidata")) return false;
            }
        } catch (IOException | InterruptedException e) {
            e.printStackTrace();
        }
        return true;
    }

    private static boolean isContainBIChange(String filePath) {
        Process process;
        try {
            String command = "grep \"diff --git\" " + filePath + " | " +
                    "awk -F\"/\" '{print $2}' && grep \"diff --git\" " + filePath + " | " +
                    "awk -F\"b/\" '{print $2}' | awk -F\"/\" '{print $1}'";
            System.out.println(command);
            process = Runtime.getRuntime().exec(new String[]{"/bin/sh", "-c", command});
            process.waitFor();
            BufferedReader br = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;
            while ((line = br.readLine()) != null) {
                System.out.println(line);
                if (line.equals("polars-bi")) return true;
            }
        } catch (IOException | InterruptedException e) {
            e.printStackTrace();
        }
        return false;
    }

    private static boolean isContainHihidataChange(String filePath) {
        Process process;
        try {
            String command = "grep \"diff --git\" " + filePath + " | " +
                    "awk -F\"/\" '{print $2}' && grep \"diff --git\" " + filePath + " | " +
                    "awk -F\"b/\" '{print $2}' | awk -F\"/\" '{print $1}'";
            System.out.println(command);
            process = Runtime.getRuntime().exec(new String[]{"/bin/sh", "-c", command});
            process.waitFor();
            BufferedReader br = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;
            while ((line = br.readLine()) != null) {
                System.out.println(line);
                if (line.equals("polars-hihidata")) return true;
            }
        } catch (IOException | InterruptedException e) {
            e.printStackTrace();
        }
        return false;
    }

    private static boolean isContainPriorityFileChanges(String filePath) {
        Process process;
        try {
            String command = "grep \"diff --git\" " + filePath + " | " +
                    "awk -F\"/\" '{print $2}' && grep \"diff --git\" " + filePath + " | " +
                    "awk -F\"b/\" '{print $2}' | awk -F\"/\" '{print $1}'";
            System.out.println(command);
            process = Runtime.getRuntime().exec(new String[]{"/bin/sh", "-c", command});
            process.waitFor();
            BufferedReader br = new BufferedReader(new InputStreamReader(process.getInputStream()));
            String line;
            while ((line = br.readLine()) != null) {
                System.out.println(line);
                if (line.equals("polars-bi")) return true;
            }
        } catch (IOException | InterruptedException e) {
            e.printStackTrace();
        }
        return false;
    }

    public static byte[] readInputStream(InputStream inputStream) {
        byte[] buffer = new byte[1024];
        int len = 0;
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try {
            while ((len = inputStream.read(buffer)) != -1) bos.write(buffer, 0, len);

        } catch (IOException e) {
            e.printStackTrace();
        } finally {
            try {
                if (bos != null) {
                    bos.close();
                }
            } catch (IOException ioe) {
                ioe.printStackTrace();
            }
        }
        return bos.toByteArray();
    }

    public Boolean PrIsOpen(){
        if("OPEN".equals(response.get("state"))){
            return true;
        }
        return false;
    }

    private StringBuffer getPrResponse(String prId) {
        String url = "https://code.fineres.com/rest/api/latest/projects/CAL/repos/polars/pull-requests/" + prId + "/activities";
        return new StringBuffer(getGetResponse(url));
    }


//    private StringBuffer getPrResponse(String prId) {
//        StringBuffer response = new StringBuffer();
//        FutureTask<String> future = null;
//        final ExecutorService exec = Executors.newFixedThreadPool(1);
//        try {
//
//            Callable<String> call = new Callable<String>() {
//                public String call() {
//                    try {
//                        //开始执行耗时操作
//                        String url = "https://code.fineres.com/rest/api/latest/projects/CAL/repos/polars/pull-requests/" + prId + "/activities";
//                        HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
//                        connection.setRequestMethod("GET");
//                        connection.setRequestProperty("Cookie", rememberme);
//                        connection.setConnectTimeout(60 * 1000);
//                        connection.setReadTimeout(60 * 1000);
//                        connection.connect();
//                        BufferedReader in = new BufferedReader(
//                                new InputStreamReader(connection.getInputStream()));
//                        String inputLine;
//                        while ((inputLine = in.readLine()) != null) {
//                            response.append(inputLine);
//                        }
//                    } catch (IOException e) {
//                        e.printStackTrace();
//                    }
//                    return "getPr线程执行完成.";
//                }
//            };
//            future = (FutureTask<String>) exec.submit(call);
//            String obj = future.get(1000 * 70, TimeUnit.MILLISECONDS);
//            System.out.println("任务成功返回:" + obj);
//        } catch (TimeoutException ex) {
//            System.out.println("处理超时啦....");
//            ex.printStackTrace();
//            future.cancel(true);
//        } catch (Exception e) {
//            System.out.println("处理失败.");
//            e.printStackTrace();
//        } finally {
//            exec.shutdownNow();
//            while (!exec.isTerminated()) {
//            }
//        }
//        return response;
//    }

    //先统计当前次数，然后再到数据库拿到当前次数进行比较，
    public Boolean[] monitorManualTriggers(PR pr) throws Exception {

        Boolean[] res = new Boolean[]{false, false, false, false, false};

        StringBuffer response = getPrResponse(pr.getPrId());
        JSONArray jsonArray = JSON.parseObject(response.toString()).getJSONArray("values");
        for (int i = 0; i < jsonArray.size(); i++) {
            JSONObject jsonObject = jsonArray.getJSONObject(i);
            if (jsonObject.get("comment") != null) {
                JSONObject comment = (JSONObject) jsonObject.get("comment");
                pr.setOldestCreatedDate(comment.getLong("createdDate") / 1000);
            }

            if ((jsonObject.getString("addedReviewers") != null && jsonObject.getJSONArray("addedReviewers").size() != 0)
                    || jsonObject.getString("removedReviewers") != null && jsonObject.getJSONArray("removedReviewers").size() != 0) {
                pr.setLastestAddOrReMoveReviewerTime(jsonObject.getLong("createdDate"));
            }

            if (jsonObject.toString().contains("\"text\":")) {
                String text = JSON.parseObject(jsonObject.getString("comment")).getString("text");
                text = text.trim();
                if ("bot:run".equals(text)) pr.addRunCount(1);
                else if ("bot:llvm-run".equals(text)) pr.addRunLlvmCount(1);
                else if (text.equals("bot:benchmark-dict")) pr.addBenchmarkDictCount(1);
                else if (text.equals("bot:benchmark-normal")) pr.addBenchmarkNormalCount(1);
                //else if (text.equals("测试分支:polars_test11_feature\n测试通过")
                //        || text.equals("测试分支:polars_test11_feature_1\n测试通过")
                //release只走分布式计算逻辑
                //|| text.equals("测试分支:polars_test11_release\n测试通过")
                //|| text.equals("测试分支:polars_test11_release_1\n测试通过")) {
                //        || (text.contains("测试分支:polars_test11_release_dispatch") && text.contains("测试通过"))){
                //    pr.addBenchmarkNormalCount(1);
                //    pr.addBenchmarkDictCount(1);
                //else if ("测试分支:polars_test_llvm\n测试通过\nC++单测!!!".equals(text)) {
                //C++只触发normal
                //    pr.addBenchmarkllvmNormalCount(1);
                //}
            }
        }

        String sql = "select count,llvmCount,benchmark,benchmarkDict,benchmarkllvm from prIdMessage_new where prid =" + pr.getPrId();
        List<Map<String, String>> result = JSYDBUtils.query(sql, "count", "llvmCount", "benchmark", "benchmarkDict", "benchmarkllvm");
        int count = 0;
        int llvmCount = 0;
        int benchmark = 0;
        int benchmarkDict = 0;
        int benchmarkllvm = 0;
        if (result == null || result.isEmpty()) {
            sql = "INSERT INTO prIdMessage_new (prid,count,llvmCount,benchmark,benchmarkDict,benchmarkllvm) values (" + pr.getPrId() + ",0,0,0,0,0)";
            JSYDBUtils.updateData(sql);

        } else {
            Map<String, String> map = result.get(0);
            count = Integer.parseInt(map.get("count"));
            benchmark = Integer.parseInt(map.get("benchmark"));
            benchmarkDict = Integer.parseInt(map.get("benchmarkDict"));
            llvmCount = map.get("llvmCount") == null ? 0 : Integer.parseInt(map.get("llvmCount"));
            benchmarkllvm = map.get("benchmarkllvm") == null ? 0 : Integer.parseInt(map.get("benchmarkllvm"));

        }

        JSYDBUtils.updatePrTriggerCount(pr, count, pr.getRunCount(), "count");
        JSYDBUtils.updatePrTriggerCount(pr, llvmCount, pr.getRunLlvmCount(), "llvmCount");
        JSYDBUtils.updatePrTriggerCount(pr, benchmark, pr.getBenchmarkNormalCount(), "benchmark");
        JSYDBUtils.updatePrTriggerCount(pr, benchmarkDict, pr.getBenchmarkDictCount(), "benchmarkDict");
        JSYDBUtils.updatePrTriggerCount(pr, benchmarkllvm, pr.getBenchmarkllvmNormalCount(), "benchmarkllvm");

        //单测通过，需要提示合并代码
        WechatMessageUtils wechatMessageUtils = new WechatMessageUtils();
        JSONObject textMessage = new JSONObject();
        textMessage.put("msgtype", "text");
        JSONObject textContent = new JSONObject();
        textContent.put("content", "https://code.fineres.com/projects/CAL/repos/polars/pull-requests/" + pr.getPrId() + "/overview 单测通过");
        textContent.put("mentioned_list", Arrays.asList(pr.getBuilder()));
        textMessage.put("text", textContent);

        if (pr.getRunCount() > count) res[0] = true;
        if (pr.getBenchmarkNormalCount() > benchmark) {
            wechatMessageUtils.sendMessageToWeChat(textMessage.toString(), "0e8df370-dac0-45de-84e7-a2ee049ad34a", pr.getBuilder());
            res[1] = true;
        }
        //停掉字典类型的benchmark
        //if (pr.getBenchmarkDictCount() > benchmarkDict) res[2] = true;
        if (pr.getRunLlvmCount() > llvmCount) res[3] = true;
        if (pr.getBenchmarkllvmNormalCount() > benchmarkllvm) {
            // 发送消息
            wechatMessageUtils.sendMessageToWeChat(textMessage.toString(), "0e8df370-dac0-45de-84e7-a2ee049ad34a", pr.getBuilder());
            res[4] = true;
        }

        return res;
    }

    public Queue<PR> getResultPRQueue(String branch, int deep, String codeType) throws Exception {
        Queue<PR> queue = new LinkedList();
        int start = 0;
        while (queue.size() < deep && start < 100) {
            String url = "https://code.fineres.com/projects/CAL/repos/polars/pull-requests?state=MERGED" + "&start=" + start + "&reviewer=";
            start += 25;

            URLConnection urlConnection = new URL(url).openConnection();
            urlConnection.setRequestProperty("Cookie", cookie);
            HttpURLConnection connection = (HttpURLConnection) urlConnection;
            connection.setRequestMethod("GET");
            connection.setConnectTimeout(5000);
            connection.connect();

            StringBuffer response = new StringBuffer();

            BufferedReader in = new BufferedReader(
                    new InputStreamReader(urlConnection.getInputStream()));
            String inputLine;

            while ((inputLine = in.readLine()) != null) {
                response.append(inputLine);
            }

            JSONArray jsonArray = JSON.parseArray(response.toString().split("\"values\":")[1].split(",\"start\":")[0]);
            for (int i = 0; i < jsonArray.size(); i++) {
                JSONObject jsonObject = jsonArray.getJSONObject(i);
                String prId = jsonObject.getString("id");
                String displayId = jsonObject.getJSONObject("toRef").getString("displayId");
                String author = jsonObject.getJSONObject("author").getJSONObject("user").getString("displayName");

                PR pr = new PR(displayId, author, prId);
                pr.setCodeType(codeType);
                //1.检查分支是否相等，2.检查数据库是否存在相应代码类型的结果 3.不需要检查结果是否完整，结果不完整的话写不到数据库中
                if (displayId.equals(branch)) {
                    //还是按照之前的合并前跑，如果耗时长，就分分支去跑不同用例集
                    Boolean isExitBenchMarkResult = JSYDBUtils.isExitBenchMarkResult(pr);
                    if (isExitBenchMarkResult) {
                        pr.setCodeType(codeType);
                        if (queue.size() < deep) {
                            queue.add(pr);
                            System.out.println("added to the queue : " + pr.getPrId());
                        } else {
                            break;
                        }
                    }
                }
            }
        }
        return queue;
    }

    public Queue<PR> getPRQueue(String branch) throws Exception {
        Queue<PR> queue = new LinkedList();
        int start = 0;
        while (start < 300) {
            String url = "https://code.fineres.com/projects/CAL/repos/polars/pull-requests?state=MERGED" + "&start=" + start + "&reviewer=";
            start += 25;

            URLConnection urlConnection = new URL(url).openConnection();
            urlConnection.setRequestProperty("Cookie", cookie);
            HttpURLConnection connection = (HttpURLConnection) urlConnection;
            connection.setRequestMethod("GET");
            connection.setConnectTimeout(5000);
            connection.connect();

            StringBuffer response = new StringBuffer();

            BufferedReader in = new BufferedReader(
                    new InputStreamReader(urlConnection.getInputStream()));
            String inputLine;

            while ((inputLine = in.readLine()) != null) {
                response.append(inputLine);
            }

            JSONArray jsonArray = JSON.parseArray(response.toString().split("\"values\":")[1].split(",\"start\":")[0]);
            for (int i = 0; i < jsonArray.size(); i++) {
                JSONObject jsonObject = jsonArray.getJSONObject(i);
                String prId = jsonObject.getString("id");
                String displayId = jsonObject.getJSONObject("toRef").getString("displayId");
                String author = jsonObject.getJSONObject("author").getJSONObject("user").getString("displayName");

                PR pr = new PR(displayId, author, prId);
                if (displayId.equals(branch)) {
                    Boolean isExitBenchMarkResult = JSYDBUtils.isExitBenchMarkResult(pr);
                    if (isExitBenchMarkResult) {
                        if (queue.isEmpty()) {
                            queue.add(pr);
                            continue;
                        }
                        break;
                    }
                    queue.add(pr);
                }
            }
        }
        return queue;
    }



    /*public PR getLastPr(PR pr) throws IOException {
        int key = 1;
        while (key != 3) {
            String url = "https://code.fineres.com/projects/CAL/repos/polars/pull-requests?state=MERGED" + "&start=" + 0 + "&reviewer=";
            URLConnection urlConnection = new URL(url).openConnection();
            urlConnection.setRequestProperty("Cookie", cookie);
            HttpURLConnection connection = (HttpURLConnection) urlConnection;
            connection.setRequestMethod("GET");
            connection.setConnectTimeout(5000);
            connection.connect();

            StringBuffer response = new StringBuffer();

            BufferedReader in = new BufferedReader(
                    new InputStreamReader(urlConnection.getInputStream()));
            String inputLine;

            while ((inputLine = in.readLine()) != null) {
                response.append(inputLine);
            }

            JSONArray jsonArray = JSON.parseArray(response.toString().split("\"values\":")[1].split(",\"start\":")[0]);
            for (int i = 0; i < jsonArray.size(); i++) {
                JSONObject jsonObject = jsonArray.getJSONObject(i);
                String prId = jsonObject.getString("id");
                if(key == 2){
                    //创建PR
                    String displayId = jsonObject.getJSONObject("toRef").getString("displayId");
                    String author = jsonObject.getJSONObject("author").getJSONObject("user").getString("displayName");
                    pr = new PR(displayId, author, prId);
                    pr.setCodeType();
                    key++;
                }
                if (prId.equals(pr.getPrId())) {
                    key += 1;
                    break;
                }
            }
        }
    }*/
}
