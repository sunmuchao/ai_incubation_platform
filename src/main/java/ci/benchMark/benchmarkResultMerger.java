package ci.benchMark;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.opencsv.CSVReader;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLConnection;
import java.util.*;

public class benchmarkResultMerger {
    static String curpath = "/data/ContinuousIntegration/polars_test-benchmark/";
    private static String masterpath = curpath + "master.csv";
    private static String releasepath = curpath + "release.csv";
    private static String devpath = curpath + "dev.csv";
    private static String strategypath = curpath + "strategy.csv";
    private static ArrayList<String> propers = new ArrayList();

    public static void showResult(String prid, String branch, String dataType) throws IOException {
        System.out.println(curpath);
        try {
            //设置devpath releasepath masterpath
            ArrayList<Deque> pathList = (ArrayList<Deque>) getLatestMergedPrid();
            Deque releaseDeque = pathList.get(1);
            Deque masterDeque = pathList.get(2);
            Deque devDeque = null;
            if (branch.equals("feature")) devDeque = pathList.get(0);

            while (!devDeque.isEmpty()) {
                String mergedDevPird = (String) devDeque.removeLast();
                devpath = curpath + mergedDevPird + "-" + dataType + ".csv";
                File devFile = new File(devpath);
                if (!devFile.exists())
                    continue;
                else
                    break;
            }

            while (!releaseDeque.isEmpty()) {
                String mergedReleasePird = (String) releaseDeque.removeLast();
                releasepath = curpath + mergedReleasePird + "-" + dataType + ".csv";
                File devFile = new File(releasepath);
                if (!devFile.exists())
                    continue;
                else
                    break;
            }

            while (!masterDeque.isEmpty()) {
                String mergedMasterPird = (String) masterDeque.removeLast();
                masterpath = curpath + mergedMasterPird + "-" + dataType + ".csv";
                File devFile = new File(masterpath);
                if (!devFile.exists())
                    continue;
                else
                    break;
            }

            List<String> baseLineList = new ArrayList<>();
            baseLineList.add(devpath);
            baseLineList.add(releasepath);
            //baseLineList.add(masterpath);

            LinkedHashSet errSet = new LinkedHashSet();
            LinkedHashSet upSet = new LinkedHashSet();
            LinkedHashSet fallSet = new LinkedHashSet();
            LinkedHashSet normalSet = new LinkedHashSet();
            LinkedHashSet latestSet = new LinkedHashSet();

            Map<String, LinkedHashSet> onlyPrintNewMap = new HashMap();
            Map<String, LinkedHashSet> PrintAllMap = new HashMap();

            ArrayList score = null;
            strategypath = curpath + prid + "-" + dataType + ".csv";
            for (int i = 0; i < baseLineList.size(); i++) {
                System.out.println(baseLineList.get(i));
                Map<String, List> resMap = parseCompareResult(baseLineList.get(i), strategypath);

                latestSet.addAll((ArrayList) resMap.get("新增"));
                errSet.addAll((ArrayList) resMap.get("错误"));
                fallSet.addAll((ArrayList) resMap.get("性能下降"));
                upSet.addAll((ArrayList) resMap.get("性能提升"));
                normalSet.addAll((ArrayList) resMap.get("性能无变化"));

                if (branch.equals("feature") && i == 0)
                    score = (ArrayList) resMap.get("性能平均分");
                else if (branch.equals("release") && i == 1)
                    score = (ArrayList) resMap.get("性能平均分");
            }

            onlyPrintNewMap.put("新增", latestSet);
            onlyPrintNewMap.put("错误", errSet);

            PrintAllMap.put("性能下降", fallSet);
            PrintAllMap.put("性能提升", upSet);
            PrintAllMap.put("性能无变化", normalSet);

            StringBuilder stringHtml = new StringBuilder();
            int number = 1;
            //打开文件
            File file = new File(curpath + "html/" + prid + "-" + dataType + "-" + number + ".html");
            while (file.exists()) {
                number += 1;
                file = new File(curpath + "html/" + prid + "-" + dataType + "-" + number + ".html");
            }

            PrintStream printStream = new PrintStream(new FileOutputStream(file));

            //输入HTML文件内容
            stringHtml.append("<html><head><meta http-equiv=\"Content-Type\" content=\"text/html; " +
                    "charset=UTF-8\"><title>BrachMasrk测试报告</title></head><body><div></div>");


            //将csv文件放入到内存中
            Map<String, ArrayList> csvMap = new HashMap();
            csvMap.put("strategy", new ArrayList());
            csvMap.put("release", new ArrayList());
            csvMap.put("dev", new ArrayList());

            Map<String, CSVReader> readerMap = new HashMap();
            readerMap.put("strategy", new CSVReader(new FileReader(strategypath)));
            readerMap.put("release", new CSVReader(new FileReader(releasepath)));
            readerMap.put("dev", new CSVReader(new FileReader(devpath)));

            String[] line;
            for (Map.Entry<String, CSVReader> reader : readerMap.entrySet()) {
                while ((line = reader.getValue().readNext()) != null) {
                    csvMap.get(reader.getKey()).add(line);
                }
            }


            for (Map.Entry<String, LinkedHashSet> entry : onlyPrintNewMap.entrySet()) {
                String name = entry.getKey();
                Set<String> set = entry.getValue();
                Iterator iterator = set.iterator();
                if (!set.isEmpty() && !stringHtml.toString().contains(name + "用例"))
                    stringHtml.append("<table border=\"1\"><h2>" + name + "用例</h2><tr>");

                while (iterator.hasNext()) {
                    Long UUID = (Long) iterator.next();
                    try {
                        ArrayList<String[]> strategyList = csvMap.get("strategy");
                        strategyList.forEach(l -> {
                            if (String.valueOf((l[0] + l[1] + l[2]).hashCode()).equals(String.valueOf(UUID))) {
                                System.out.println(name + "列表：" + l[0] + l[1] + l[2]);

                                stringHtml.append("<td bgcolor=\"#00FF00\">");
                                for (String s : propers)
                                    stringHtml.append("<td bgcolor=\"#00FF00\">" + s + "</td>\n");
                                stringHtml.append("</td>");
                                stringHtml.append("</tr><tr>\n");

                                for (String s : l) stringHtml.append("<td>" + s + "</td>\n");
                                stringHtml.append("<td><a href=\"http://192.168.5.22:8082/pls/" + l[2] + "\">下载pls</a></td>\n");
                                stringHtml.append("<td><a href=\"http://192.168.5.22:8082/suite/" + l[2].split(".")[0] + ".suite2" + "\">下载suite</a></td></tr>\n");
                            }
                        });
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
            }

            for (Map.Entry<String, LinkedHashSet> entry : PrintAllMap.entrySet()) {
                String name = entry.getKey();
                Set<String> set = entry.getValue();
                Iterator iterator = set.iterator();
                if (!set.isEmpty() && !stringHtml.toString().contains(name + "用例"))
                    stringHtml.append("<table border=\"1\"><h2>" + name + "用例</h2><tr>");
                while (iterator.hasNext()) {
                    Long UUID = (Long) iterator.next();
                    ArrayList<String[]> strategyList = csvMap.get("strategy");
                    strategyList.forEach(l -> {
                        if (String.valueOf((l[0] + l[1] + l[2]).hashCode()).equals(String.valueOf(UUID))) {
                            System.out.println(name + "列表：" + l[0] + l[1] + l[2]);
                            stringHtml.append("<td bgcolor=\"#00FF00\">");
                            for (String s : propers) stringHtml.append("<td bgcolor=\"#00FF00\">" + s + "</td>\n");
                            stringHtml.append("</td>");
                            stringHtml.append("</tr><tr><td>" + "当前用例" + "</td>");

                            for (String s : l) stringHtml.append("<td>" + s + "</td>\n");
                            stringHtml.append("<td><a href=\"http://192.168.5.22:8082/pls/" + l[2] + "\">下载pls</a></td>\n");
                            stringHtml.append("<td><a href=\"http://192.168.5.22:8082/suite/" + l[2].split("\\.")[0] + ".suite2" + "\">下载suite</a></td></tr>\n");
                        }
                    });

                    for (Map.Entry<String, ArrayList> entrySet : csvMap.entrySet()) {
                        if (entrySet.getKey().equals("strategy")) continue;
                        ArrayList<String[]> lines = entrySet.getValue();
                        lines.forEach(l -> {
                            if (UUID == (l[0] + l[1] + l[2]).hashCode()) {
                                stringHtml.append("<tr><td>" + entrySet.getKey() + "用例" + "</td>");
                                System.out.println(l[2]);
                                for (String s : l) stringHtml.append("<td>" + s + "</td>\n");
                                stringHtml.append("</tr>\n");
                            }
                        });
                    }
                }

            }
            stringHtml.append("</body></html>");

            //将HTML文件内容写入文件中
            printStream.println(stringHtml.toString());

            //新增用例数和错误用例数写入本地文件
            file = new File(curpath + "inject_variables.properties");
            if (!file.exists()) file.createNewFile();
            System.out.println("newCaseCount=" + latestSet.size() + "\nerrCaseCount=" + errSet.size() +
                    "\nfallCaseCount=" + fallSet.size() + "\nupCaseCount" + upSet.size() + "\nnormalCount" + normalSet.size() +
                    "\navgScore=" + score.get(0) + "\navgConScore=" + score.get(1));

            new PrintStream(new FileOutputStream(file)).println("newCaseCount=" + latestSet.size() + "\nerrCaseCount=" + errSet.size() +
                    "\nfallCaseCount=" + fallSet.size() + "\nupCaseCount=" + upSet.size() + "\nnormalCount=" + normalSet.size() +
                    "\navgScore=" + score.get(0) + "\navgConScore=" + score.get(1) +  "\nnumber="+number);
        } catch (
                IOException e) {
            e.printStackTrace();
        }
    }

    private static Map parseCompareResult(String baseLine, String strategypath) throws IOException {
        CSVReader csvReader = null;
        Map<String, ArrayList> resMap = new LinkedHashMap();
        try {
            Process pid1 = Runtime.getRuntime().exec("grep \"resultPath\" ./csvCompare.properties | tr '=' '\n' |  sed -n '2p'");
            BufferedReader br = new BufferedReader(new InputStreamReader(pid1.getInputStream()));
            String resultPath = br.readLine();

            //执行tool类，生成结果文件
            Runtime.getRuntime().exec("java -cp ./code/polars/polars-benchmark/target/polars-benchmark-1.0-SNAPSHOT.jar" +
                    " com.fanruan.polars.benchmark.compar.CsvResultCompareTool ./csvCompare.properties " + baseLine + " " + strategypath);

            //解析结果文件，生成resList
            csvReader = new CSVReader(new FileReader(resultPath));
            String[] lines;
            while ((lines = csvReader.readNext()) != null) {
                String listName = null;
                if (lines.length == 1) {
                    listName = lines[0].split(":")[0];
                    resMap.put(listName, new ArrayList());
                    lines = csvReader.readNext();
                    for (String l : lines)
                        propers.add(l);
                } else {
                    if (lines[0].equals("strategy用例:")) {
                        resMap.get(listName).add(lines[1] + "_" + lines[2] + "_" + lines[3]);
                    }
                }
            }
        } catch (FileNotFoundException e) {
            e.printStackTrace();
        } finally {
            csvReader.close();
        }
        return resMap;
    }

    public static List<Deque> getLatestMergedPrid() {
        List<Deque> res = new ArrayList<>();
        int start = 0;
        Deque<String> devPrIdDeque = new LinkedList<>();
        Deque<String> releasePrIdDeque = new LinkedList<>();
        Deque<String> masterPrIdDeque = new LinkedList<>();
        try {
            while (devPrIdDeque.size() == 0 || releasePrIdDeque.size() == 0) {
                String cookie = getCookie();

                String url = "https://code.fineres.com/projects/CAL/repos/polars/pull-requests?state=MERGED"+"&start=" + start + "&reviewer=";
                start += 25;
                URLConnection urlConnection = new URL(url).openConnection();
                urlConnection.setRequestProperty("Cookie", cookie);
                HttpURLConnection connection = (HttpURLConnection) urlConnection;
                connection.setRequestMethod("GET");
                connection.connect();

                BufferedReader in = new BufferedReader(
                        new InputStreamReader(urlConnection.getInputStream()));
                String inputLine;
                StringBuffer response = new StringBuffer();

                while ((inputLine = in.readLine()) != null) {
                    response.append(inputLine);
                }
                JSONArray jsonArray = JSON.parseArray(response.toString().split("\"values\":")[1].split(",\"start\":")[0]);

                for (int i = 0; i < jsonArray.size(); i++) {
                    JSONObject jsonObject = jsonArray.getJSONObject(i);
                    String prId = jsonObject.getString("id");
                    JSONObject toRef = (JSONObject) JSON.parse(jsonObject.getString("toRef"));
                    String displayId = toRef.getString("displayId");

                    if (displayId.equals("feature/3.0")) {
                        System.out.println("feature:" + prId);
                        devPrIdDeque.add(prId);
                    } else if (displayId.equals("release/3.0")) {
                        System.out.println("release:" + prId);
                        releasePrIdDeque.add(prId);
                    } else if (displayId.equals("release/master")) {
                        System.out.println("master:" + prId);
                        masterPrIdDeque.add(prId);
                    }
                }
            }
            res.add(devPrIdDeque);
            res.add(releasePrIdDeque);
            res.add(masterPrIdDeque);
        } catch (IOException e) {
            e.printStackTrace();
        }

        return res;
    }

    public static String getCookie() {
        String url = "https://code.fineres.com/j_atl_security_check";
        URLConnection urlConnection;
        String rememberme = null;
        while (true) {
            try {
                String param = "j_username=Frank.Niu&j_password=Maxnxl555!&_atl_remember_me=on&submit=登录&scan=企业微信扫码登录";
                urlConnection = new URL(url).openConnection();
                HttpURLConnection conn = (HttpURLConnection) urlConnection;
                conn.setInstanceFollowRedirects(false);
                conn.setDoOutput(true);
                conn.setDoInput(true);
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Cookie", "_ga=GA1.2.145599097.1623144057; SPC-SELECTED-CATEGORY-CORE=all; SPC-SELECTED-CATEGORY=18; BITBUCKETSESSIONID=34C6CC0F403F81E0228EC169B4904E4D");
                OutputStream os = conn.getOutputStream();
                if (param != null && param.length() > 0) os.write(param.getBytes());
                if (conn.getResponseCode() == 302) {
                    rememberme = conn.getHeaderField("Set-Cookie").split(";")[0];
                    break;
                }
                Thread.sleep(2000);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return rememberme;
    }
}
