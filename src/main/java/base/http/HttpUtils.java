package base.http;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.MalformedURLException;
import java.net.URL;
import java.net.URLConnection;

public class HttpUtils {
    private int responseCode = 0;
    private String url;
    private String cookie;

    public HttpUtils(String url, String cookie) {
        this.url = url;
        this.cookie = cookie;
    }

    public String connectAndGetRequest() throws IOException {
        URLConnection urlConnection = null;
        BufferedReader reader = null;
        String inputLine = null;
        StringBuffer response = new StringBuffer();
        try {
            System.out.println("get-url = " + url);
            urlConnection = new URL(url).openConnection();
            HttpURLConnection connection = (HttpURLConnection) urlConnection;
            connection.setRequestMethod("GET");
            connection.setRequestProperty("cookie", cookie);
            connection.connect();
            reader = new BufferedReader(
                    new InputStreamReader(urlConnection.getInputStream()));
            while ((inputLine = reader.readLine()) != null) {
                response.append(inputLine);
            }

            if (response.toString().contains("503 ")) {
//                System.out.println(response.toString());
                responseCode = 503;
            }

            //System.out.println(response.toString());
        } catch (IOException e) {
            e.printStackTrace();
        } finally {
            if(reader != null) reader.close();
        }
        return response.toString();
    }

    public int getResponseCode() {
        return responseCode;
    }


    public String connectAndGetPostRequest( String params) {
        String msg = "";
        try {
            System.out.println("post-url = " + url);
            HttpURLConnection connection = (HttpURLConnection) new URL(url).openConnection();
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(3000);
            connection.setDoOutput(true);
            connection.setDoInput(true);
            connection.setUseCaches(false);
            connection.setRequestProperty("cookie", cookie);
            connection.setRequestProperty("Content-Type", "application/json;charset=UTF-8");
            connection.connect();
            /* 4. 处理输入输出 */
            // 写入参数到请求中
            OutputStream out = connection.getOutputStream();
            out.write(params.getBytes());
            out.flush();
            out.close();
            // 从连接中读取响应信息

            int code = connection.getResponseCode();
            if (code == 200) {
                BufferedReader reader = new BufferedReader(new InputStreamReader(connection.getInputStream()));
                String line;
                while ((line = reader.readLine()) != null) {
                    msg += line + "\n";
                }
                reader.close();
            }
            // 5. 断开连接
            connection.disconnect();
        } catch (MalformedURLException e) {
            e.printStackTrace();
        } catch (IOException e) {
            e.printStackTrace();
        }
        return msg;
    }
}

