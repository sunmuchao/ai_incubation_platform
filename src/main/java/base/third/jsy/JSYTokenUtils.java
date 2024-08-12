package base.third.jsy;

import com.alibaba.fastjson.JSONPath;
import okhttp3.*;

import java.io.IOException;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.TimeUnit;

public class JSYTokenUtils {
    private static final OkHttpClient client = new OkHttpClient().newBuilder()
            .readTimeout(60, TimeUnit.SECONDS)
            .connectTimeout(60,TimeUnit.SECONDS)
            .followRedirects(false)
            .build();
    private static final OkHttpClient followRedirectClient = new OkHttpClient().newBuilder()
            .readTimeout(60,TimeUnit.SECONDS)
            .connectTimeout(60,TimeUnit.SECONDS)
            .build();

    public static String getToken(String userName,String passWord){
        String token = "";
        String tokenUrl = getTokenUrl(userName, passWord);
        Request request = new Request.Builder()
                .addHeader("Content-Type","application/x-www-form-urlencoded")
                .addHeader("Connection","keep-alive")
                .url(tokenUrl)
                .build();
        Response response = null;
        try {
            response = client.newCall(request).execute();
            List<String> headers = response.headers("Set-Cookie");
            for (String header:headers){
                if (header.contains("fine_auth_token=")){
                    token = header.split("fine_auth_token=")[1].split(";")[0];
                    System.out.println("token = "+token);
                    return token;
                }
            }
        } catch (IOException e) {
            e.printStackTrace();
        }

        return token;
    }

    private static String getTokenUrl(String userName,String passWord){
        String tokenUrl = "";
        RequestBody formBody = new FormBody.Builder()
                .add("mobile", userName)
                .add("password", passWord)
                .add("referrer","https://work.jiushuyun.com/decision/home")
                .add("app","jiushuyun")
                .build();
        Request request = new Request.Builder()
                .addHeader("Content-Type","application/x-www-form-urlencoded")
                .addHeader("Connection","keep-alive")
                .url("https://fanruanclub.com/login/verify")
                .post(formBody)
                .build();
        Response response = null;
        try {
            response = followRedirectClient.newCall(request).execute();
            if (response.body()==null) return tokenUrl;
            tokenUrl = JSONPath.read(Objects.requireNonNull(response.body()).string(),
                    "$.data.redirectUrl").toString();
            System.out.println(tokenUrl);
        } catch (IOException e) {
            e.printStackTrace();
        }
        return tokenUrl;

    }


}
