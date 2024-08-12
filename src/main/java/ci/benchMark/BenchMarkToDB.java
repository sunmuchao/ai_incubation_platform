package ci.benchMark;

import buriedPoint.DBUtils;
import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.opencsv.CSVReader;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLConnection;
import java.util.ArrayList;
import java.util.Deque;
import java.util.LinkedList;
import java.util.List;

import base.config.Application;

public class BenchMarkToDB {
    static String curpath = "/opt/ContinuousIntegration/polars_test-benchmark/";
    //static String curpath = "/Users/sunmuchao/Downloads/benchmark/";
    public static List<Deque> getTop100MergedPrid() {
        List<Deque> res = new ArrayList<>();
        int start = 0;
        Deque<String> featurePrIdDeque = new LinkedList<>();
        Deque<String> releasePrIdDeque = new LinkedList<>();
        try {
            while (featurePrIdDeque.size() < 25 || releasePrIdDeque.size() < 25) {
                String cookie = getCookie();

                String url = "https://code.fineres.com/projects/CAL/repos/polars/pull-requests?state=MERGED" + "&start=" + start + "&reviewer=";
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
                        featurePrIdDeque.add(prId);
                    } else if (displayId.equals("release/3.0")) {
                        System.out.println("release:" + prId);
                        releasePrIdDeque.add(prId);
                    }
                }
            }
            res.add(featurePrIdDeque);
            res.add(releasePrIdDeque);
        } catch (IOException e) {
            e.printStackTrace();
        }

        return res;
    }

    public static void CsvToDB(String dataType) {
        List<Deque> prIdDeques = getTop100MergedPrid();
        DBUtils dbUtils = Application.getDBUtilsInstance();
        boolean open = false;
        try {
            String[] PrIdAndBuildId = dbUtils.getPrIdAndBuildId(dataType).split("_");
            String prId = null;
            int buildId = 0;
            if (!PrIdAndBuildId[0].equals("null")) {
                prId = PrIdAndBuildId[0];
                buildId = Integer.valueOf(PrIdAndBuildId[1]);
            }else {
                open = true;
            }
            for (int i = 0; i < prIdDeques.size(); i++) {
                while (prIdDeques.get(i) != null && !prIdDeques.get(i).isEmpty()) {
                    String mergedPird = (String) prIdDeques.get(i).removeLast();
                    if (mergedPird.equals(prId)) {
                        open = true;
                        continue;
                    }
                    if (open) {
                        String csvPath = curpath + mergedPird + "-" + dataType.toLowerCase()  + ".csv";
                        File csvFile = new File(csvPath);
                        if (!csvFile.exists() || csvFile.length() == 0)
                            continue;
                        else {
                            CSVReader csvReader = new CSVReader(new FileReader(csvPath));
                            String[] line;
                            csvReader.readNext();
                            String branch = null;
                            if (i == 0) branch = "feature";
                            else if (i == 1) branch = "release";
                            buildId++;
                            while ((line = csvReader.readNext()) != null) {
                                dbUtils.benchmarkIntoDB(line, mergedPird, buildId, branch, dataType);
                            }
                        }
                    }
                }
            }

        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public static String getCookie() {
        String url = "https://code.fineres.com/j_atl_security_check";
        URLConnection urlConnection;
        String rememberme = null;
        try {
            String param = "j_username=Sun.Sun&j_password=sunmuchao980320$$&_atl_remember_me=on&submit=登录&scan=企业微信扫码登录";
            urlConnection = new URL(url).openConnection();
            HttpURLConnection conn = (HttpURLConnection) urlConnection;
            conn.setInstanceFollowRedirects(false);
            conn.setDoOutput(true);
            conn.setDoInput(true);
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Cookie", "_ga=GA1.2.145599097.1623144057; SPC-SELECTED-CATEGORY-CORE=all; SPC-SELECTED-CATEGORY=18; BITBUCKETSESSIONID=34C6CC0F403F81E0228EC169B4904E4D");
            OutputStream os = conn.getOutputStream();
            if (param != null && param.length() > 0) os.write(param.getBytes());
            rememberme = conn.getHeaderField("Set-Cookie").split(";")[0];
        } catch (Exception e) {
            e.printStackTrace();
        }
        return rememberme;
    }

    public static void main(String[] args) {
        String dataType = args[0];
        CsvToDB(dataType);
    }
}
