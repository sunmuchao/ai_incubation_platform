package base.third.maven;

import cn.hutool.core.io.FileUtil;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.alibaba.fastjson.JSONPath;
import okhttp3.*;
import org.apache.commons.lang3.StringUtils;

import java.io.*;
import java.time.Instant;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

public class MavenUtils {

    private static final OkHttpClient client = new OkHttpClient().newBuilder()
            .readTimeout(60, TimeUnit.SECONDS)
            .connectTimeout(60,TimeUnit.SECONDS)
            .build();
    
    
    public static void downloadJar(String url, String saveDir, String name){
        File dir = new File(saveDir);
        if (!dir.exists()) {
            dir.mkdirs(); // 创建目录及其所有父目录
        }
        String filePath = saveDir + "/" + name;
        if (FileUtil.exist(filePath)){
            System.out.println(filePath + "重复，删除之前的");
            FileUtil.del(filePath);
        }
        System.out.println("开始从"+url+"下载jar");
        Request request = new Request.Builder()
                .url(url)
                .build();
        ResponseBody body = null;
        try {
            Response response = client.newCall(request).execute();
            body = response.body();
            InputStream inputStream = body != null ? body.byteStream() : null;
            BufferedInputStream bufferedInputStream = new BufferedInputStream(inputStream);
            FileOutputStream fileOutputStream = new FileOutputStream(filePath);
            byte[] buffer = new byte[512];
            int len;
            while ((len = bufferedInputStream.read(buffer)) != -1) {
                fileOutputStream.write(buffer, 0, len);
            }
            fileOutputStream.flush();
            fileOutputStream.close();
            bufferedInputStream.close();
        } catch (IOException e) {
            System.out.println(e.getMessage());
        }finally {
            if (body != null) {
                body.close();
            }
        }
        
    }

    public static JarVersion getJarVersion(String jarName){
        List<JarVersion> allJars = getAllJars(jarName);
        System.out.println("allJars.size() = " + allJars.size());
        getJarVersion(jarName,allJars);
        long newTime = 0L;
        JarVersion newJarVersion = new JarVersion();
        newJarVersion.setVersion("0.0.0-sn");
        for (JarVersion jarVersion : allJars) {
            if (jarVersion.getVersion().startsWith("6.") || !jarVersion.getRepositoryName().equals("fanruan")) continue;
            System.out.println(jarVersion.getId()+" : jarVersion.getTime() = "+jarVersion.getTime());
//            if (jarVersion.getTime()>newTime){
//                newTime = jarVersion.getTime();
//                newJarVersion = jarVersion;
//            }
            if (isLater(jarVersion,newJarVersion)){
                newJarVersion = jarVersion;
            }
        }
        System.out.println("jar版本为"+newJarVersion);
        return newJarVersion;
    }

    private static boolean isLater(JarVersion jarVersionA,JarVersion jarVersionB){
        System.out.println(jarVersionA);
        String idA = jarVersionA.getVersion(), idB = jarVersionB.getVersion();
        String versionA = idA.split("-")[0], versionB = idB.split("-")[0];
        System.out.println("versionA = " + versionA);
        System.out.println("versionB = " + versionB);
        return compareVersion(versionA,versionB)>0;
    }

    private static int compareVersion(String version1, String version2) {
        String[] v1 = version1.split("\\.");
        String[] v2 = version2.split("\\.");

        int i = 0;
        while (i < v1.length && i < v2.length) {
            int num1 = Integer.parseInt(v1[i]);
            int num2 = Integer.parseInt(v2[i]);

            if (num1 < num2) {
                return -1;
            } else if (num1 > num2) {
                return 1;
            }

            i++;
        }
        // If all the common parts are equal, longer version is greater
        return Integer.compare(v1.length, v2.length);
    }

    private static void getJarVersion(String jarName,List<JarVersion> allJars) {
        for (JarVersion jarVersion : allJars) {
            String stringBody = "{\"action\":\"coreui_Component\",\"method\":\"readComponentAssets\",\"data\":[{\"page\":1,\"start\":0,\"limit\":25,\"filter\":[{\"property\":\"repositoryName\",\"value\":\""+jarVersion.getRepositoryName()+"\"},{\"property\":\"componentModel\",\"value\":\"{\\\"id\\\":\\\""+jarVersion.getId()+"\\\",\\\"repositoryName\\\":\\\""+jarVersion.getRepositoryName()+"\\\",\\\"group\\\":\\\""+jarVersion.getGroup()+"\\\",\\\"name\\\":\\\""+jarVersion.getName()+"\\\",\\\"version\\\":\\\""+jarVersion.getVersion()+"\\\",\\\"format\\\":\\\""+jarVersion.getFormat()+"\\\"}\"}]}],\"type\":\"rpc\",\"tid\":31}";
            RequestBody requestBody = FormBody.create(MediaType.parse("application/json; charset=utf-8"), stringBody);
            Request request = new Request.Builder()
                    .addHeader("Content-Type","application/json")
                    .addHeader("Connection","keep-alive")
                    .addHeader("Accept","*/*")
                    .addHeader("Host","mvn.finedevelop.com")
                    .url("http://mvn.finedevelop.com/service/extdirect")
                    .post(requestBody)
                    .build();
            Response response = null;
            try {
                response = client.newCall(request).execute();
                ResponseBody body = response.body();
                JSONArray objects = (JSONArray) JSONPath.read(body.string(), "$.result.data");
                for (Object o : objects) {
                    JSONObject jar = (JSONObject) o;
                    String name = (String) jar.get("name");
                    if (StringUtils.endsWith(name,".jar")){
                        jarVersion.setPath(name);
                        String blobUpdated = (String) jar.get("blobUpdated");
                        Instant instant = Instant.from(DateTimeFormatter.ISO_OFFSET_DATE_TIME.parse(blobUpdated));
                        long timestamp = instant.getEpochSecond();
                        jarVersion.setTime(timestamp);
                    }
                }
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }

    private static List<JarVersion> getAllJars(String jarName) {
        List<JarVersion> allJars = new ArrayList<>();
        String stringBody = "{\"action\":\"coreui_Search\",\"method\":\"read\",\"data\":[{\"page\":1,\"start\":0,\"limit\":300,\"filter\":[{\"property\":\"name.raw\",\"value\":\""+jarName+"\"}]}],\"type\":\"rpc\",\"tid\":28}";
        RequestBody requestBody = FormBody.create(MediaType.parse("application/json; charset=utf-8"), stringBody);
        Request request = new Request.Builder()
                .addHeader("Content-Type","application/json")
                .addHeader("Connection","keep-alive")
                .addHeader("Accept","*/*")
                .addHeader("Host","mvn.finedevelop.com")
                .addHeader("User-Agent","Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36")
                .url("http://mvn.finedevelop.com/service/extdirect")
                .post(requestBody)
                .build();
        Response response = null;
        try {
            response = client.newCall(request).execute();
            ResponseBody body = response.body();
            if (body==null) return allJars;
            JSONArray jars = (JSONArray) JSONPath.read(body.string(), "$.result.data");
            System.out.println(jars);
            for (Object o : jars) {
                JSONObject jar = (JSONObject) o;
                allJars.add(new JarVersion(jar.getString("format"),
                        jar.getString("group"),
                        jar.getString("id"),
                        jar.getString("name"),
                        jar.getString("repositoryName"),
                        jar.getString("version"),
                        0L,
                        null));
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
        return allJars;
    }
}
