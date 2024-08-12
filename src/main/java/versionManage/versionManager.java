package versionManage;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.io.PrintStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLConnection;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Map.Entry;

public class versionManager {
    public static void main(String[] args) throws IOException, InterruptedException, ParseException {
        //String curPath = args[0];
        String curPath = new File("").getAbsolutePath();
        System.out.println("git log --tags --simplify-by-decoration --pretty=\"format:%ai %d\"");
        Process process = Runtime.getRuntime().exec("git log --tags --simplify-by-decoration --pretty=\"format:%ai %d\"");
        /*String s = new BufferedReader(new InputStreamReader(process.getInputStream(), "UTF-8")).readLine();
        System.out.println(s);*/
        String s = "";
        BufferedReader br = new BufferedReader(new InputStreamReader(process.getInputStream()));
        String contentLine = br.readLine();
        while (contentLine != null) {
            s += contentLine;
            contentLine = br.readLine();
        }

        int exitCode = process.waitFor();
        assert exitCode == 0;
        System.out.println(s);
        Map<String, Long> version = new LinkedHashMap<>();
        String[] strs = s.split("\n");

        Map<String, ArrayList<PrMamager>> res = new LinkedHashMap<>();

        for (String str : strs) {
            SimpleDateFormat simpleDateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
            Date date = simpleDateFormat.parse(str.split(" ")[0] + " " + str.split(" ")[1]);
            if (str.contains("tag:")) {
                version.put(str.split("tag:")[1].split("\\)")[0], date.getTime());
            } else {
                continue;
            }
        }

        String preVersion = null;
        Iterator entries2 = version.entrySet().iterator();
        Map<String, PrMamager> mergedPrid = getMergedPrid();

        while (entries2.hasNext()) {
            if(res.size() > 0) {
                for (PrMamager pr : res.get(preVersion)) {
                    if (mergedPrid.containsKey(pr.getPrId())) {
                        mergedPrid.remove(pr.getPrId());
                    }
                }
            }

            Map.Entry versionEntry = (Entry) entries2.next();
            Iterator entries = mergedPrid.entrySet().iterator();
            while (entries.hasNext()) {
                Map.Entry entry = (Entry) entries.next();
                PrMamager prManager = (PrMamager) entry.getValue();
                if (Long.valueOf(prManager.getClosedDate()) > (long) versionEntry.getValue()) {
                    ArrayList<PrMamager> tmp = new ArrayList();
                    if (res.get(versionEntry.getKey()) != null) {
                        tmp = res.get(versionEntry.getKey());
                    }

                    tmp.add(prManager);
                    if (preVersion != null && Long.valueOf(prManager.getClosedDate()) < version.get(preVersion)) {
                        res.put((String) versionEntry.getKey(), tmp);
                    } else {
                        res.put((String) versionEntry.getKey(), tmp);
                    }
                }
                preVersion = (String) versionEntry.getKey();
            }

        }


        StringBuilder stringHtml = new StringBuilder();
        //打开文件
        File file = new File(curPath + "/t1.html");
        PrintStream printStream = new PrintStream(new FileOutputStream(file));

        //输入HTML文件内容
        stringHtml.append("<html><head><meta http-equiv=\"Content-Type\" content=\"text/html; " +
                "charset=UTF-8\"><title>polars版本管理</title></head><body><div></div>");

        for (Map.Entry<String, ArrayList<PrMamager>> entry : res.entrySet()) {
            String mapKey = entry.getKey();
            ArrayList<PrMamager> prMamager = entry.getValue();
            stringHtml.append("<h1> Polars Persist" + mapKey);
            System.out.println("当前版本:" + mapKey);
            stringHtml.append("</h1>");

            for (int i = 0; i < prMamager.size(); i++) {
                stringHtml.append("<div><a href=" + prMamager.get(i).link + ">[POLARS-" + prMamager.get(i).getPrId() + "]: " + prMamager.get(i).title);
                System.out.println(prMamager.get(i).title);
                stringHtml.append("</a></div>");
            }
        }
        stringHtml.append("</body></html>");

        //将HTML文件内容写入文件中
        printStream.println(stringHtml.toString());
    }

    public static Map<String, PrMamager> getMergedPrid() {
        Map<String, PrMamager> res = new LinkedHashMap<>();
        int start = 0;
        try {
            while (res.size() < 500) {
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
                    String title = jsonObject.getString("title");
                    String link = jsonObject.getJSONObject("links").getJSONArray("self").get(0).toString().split("\"")[3];
                    String closedDate = jsonObject.getString("closedDate");
                    PrMamager prMamager = new PrMamager(prId, title, closedDate, link);
                    res.put(prId, prMamager);
                }
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
        return res;
    }

    public static String getCookie() {
        String url = "https://code.fineres.com/j_atl_security_check";
        URLConnection urlConnection;
        String rememberme = null;
        try {
            String param = "j_username=Sun.Sun&j_password=fr305239&_atl_remember_me=on&submit=登录&scan=企业微信扫码登录";
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
}
