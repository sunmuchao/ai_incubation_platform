package ci.bi.unitTest;


import base.db.DBUtils;
import base.http.JSchUtil;
import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.jcraft.jsch.JSchException;
import okhttp3.*;
import org.apache.commons.lang3.StringUtils;

import java.io.IOException;
import java.util.*;
import java.util.concurrent.TimeUnit;

public class BitBucketUtils {
    private static volatile BitBucketUtils instance = null;
    private static String cookie;
    private static final String userName="Sun.Sun";
    private static final String passWord="sunmuchao980320$$";
    private static final String baseUrl="https://code.fineres.com";
    private static final MediaType JSON_BODY = MediaType.parse("application/json; charset=utf-8");
    private static final OkHttpClient client = new OkHttpClient().newBuilder()
            .readTimeout(60,TimeUnit.SECONDS)
            .connectTimeout(60,TimeUnit.SECONDS)
            .followRedirects(false)
            .build();
    private static final OkHttpClient followRedirectClient = new OkHttpClient().newBuilder()
            .readTimeout(60,TimeUnit.SECONDS)
            .connectTimeout(60,TimeUnit.SECONDS)
            .build();
    private BitBucketUtils(){
    }

    public static BitBucketUtils getInstance() {
        if (instance == null) {
            synchronized (BitBucketUtils.class) {
                if (instance == null) {
                    instance = new BitBucketUtils();
                }
            }
        }
        return instance;
    }

    public void downloadPatch(BIPR bipr){
        JSchUtil jSchUtil = new JSchUtil();
        try {
            jSchUtil.initializeSession("root","192.168.5.10","Yunzx@123");
            jSchUtil.execQuery("cd /opt/BITest && echo \"j_username=Sun.Sun&j_password=sunmuchao980320$$&_atl_remember_me=on&submit=登录&scan=企业微信扫码登录\" >> password");
            jSchUtil.execQuery("cd /opt/BITest && wget --post-file=password --cookies=on --keep-session-cookies --save-cookies=cookie.txt https://code.fineres.com/j_atl_security_check");
            jSchUtil.execQuery("cd /opt/BITest && wget --cookies=on --keep-session-cookies --load-cookies=cookie.txt https://code.fineres.com/rest/patch/1.0/projects/"+bipr.getFatherRepository()+"/repos/"+bipr.getRepository()+"/pull-requests/"+bipr.getPrId()+"/patch -O /opt/BITest/"+bipr.getRepository()+"-"+bipr.getPrId()+".patch");
            jSchUtil.execQuery("cd /opt/BITest && rm -f password && rm -f cookie.txt && rm -f j_atl_security_check*");
        } catch (JSchException e) {
            e.printStackTrace();
        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            jSchUtil.closeSession();
        }

    }

    /**
     * 获得对应仓库下的所有pr*
     * @param repository 仓库
     * @param fatherRepository 父仓库
     * @return 返回的响应体
     */
    public String getPrListResponse(String repository,String fatherRepository) {
        String url = baseUrl + "/projects/"+fatherRepository+"/repos/"+repository+"/pull-requests";
        return getGetResponse(url);
    }

    /**
     * 刷新cookie
     */
    public BitBucketUtils refreshCookie(){
        try {
            getBitBucketCookie();
        } catch (IOException e) {
            e.printStackTrace();
        }
        return this;
    }

    /**
     * 判断一个pr的某条评论是否需要进行单测*
     * @param bipr pr
     * @param text 评论
     * @param updatedDate 评论时间
     * @return 是否需要进行单测
     */
    private boolean isNeedToRunUnitTest(BIPR bipr,String text,String updatedDate) throws Exception {
        boolean result = false;
        if (text.startsWith("bot:run")){

            //查看是否有union关键字，有的话就将关联仓库记录，方便后面拿pr跑关联
            if (text.contains("union:")){
                String[] unions = text.split("union:");
                for (int index=1;index< unions.length;index++){
                    String[] union = unions[index].split(",");
                    Map<String, String> unionFactory = bipr.getUnionFactory();
                    System.out.println("union[0].trim()="+union[0].trim()+"  union[1].trim()="+union[1].trim());
                    unionFactory.put(union[0].trim(), union[1].trim());
                    bipr.setUnionFactory(unionFactory);
                }
            }

            //是否跑所有仓库
            if (text.contains("needToRunAll")){
                bipr.setNeedToRunAll(true);
            }

            //要跑的某个子模块，父模块应该包括这个子模块才能跑，且只跑子模块
            if (text.contains("subModules:")){
                String[] subModules = text.split("subModules:")[1].split(" ")[0].split(",");
                bipr.setSubModules(new ArrayList<>(Arrays.asList(subModules)));
            }


            //查询数据库中的数据，如果没有就说明该跑，有就判断上次的时间和这次的updatedDate时间比较
            String sql = "select * from bi_pr_triggers where prid='"+bipr.getPrId()+"' and repository='"+bipr.getRepository()+"' and fatherRepository='"+bipr.getFatherRepository()+"'";
            List<Map<String, String>> prTrigger = DBUtils.query(sql, "lastTriggerTime","frequency");
            if (prTrigger.isEmpty()){
                bipr.setLastTriggerTime(updatedDate);
                DBUtils.updateData("insert into bi_pr_triggers (prid,repository,fatherRepository,frequency,lastTriggerTime) values ('"+bipr.getPrId()+"', '"+bipr.getRepository()+"', '"+bipr.getFatherRepository()+"', '1', '"+bipr.getLastTriggerTime()+"')");
                result=true;
            }else {
                String lastTriggerTime = prTrigger.get(0).get("lastTriggerTime");
                bipr.setLastTriggerTime(lastTriggerTime);
                System.out.println("updatedDate="+updatedDate);
                if (!isNotNumber(updatedDate)){
                    long lastTriggerTimeStamp = Long.parseLong(bipr.getLastTriggerTime());
                    long updatedDateStamp = Long.parseLong(updatedDate);
                    System.out.println("updatedDateStamp="+updatedDateStamp);
                    System.out.println("lastTriggerTimeStamp="+lastTriggerTimeStamp);
                    if (updatedDateStamp>lastTriggerTimeStamp){
                        //此时时间戳大于数据库中记录的最后一次跑的时间戳，该跑，除此之外要向数据库中记录数据
                        int frequency = Integer.parseInt(prTrigger.get(0).get("frequency"));
                        DBUtils.updateData("update bi_pr_triggers SET lastTriggerTime='"+updatedDateStamp+"', frequency='"+(++frequency)+"' WHERE prid='"+bipr.getPrId()+"' and repository='"+bipr.getRepository()+"' and fatherRepository='"+bipr.getFatherRepository()+"'");
                        result=true;
                    }
                }
            }
        }
        return result;
    }

    /**
     * 判断是否需要进行单测
     */
    public boolean isNeedToTrigger(BIPR bipr) throws Exception {
        boolean result =false;

        String prResponse = getPrResponse(bipr);
        JSONArray jsonArray = JSON.parseObject(prResponse).getJSONArray("values");
        for (int i = 0; i < jsonArray.size(); i++) {
            JSONObject jsonObject = jsonArray.getJSONObject(i);
            if (jsonObject.toString().contains("\"text\":")) {
                String text = JSON.parseObject(jsonObject.getString("comment")).getString("text").trim();
                String updatedDate = JSON.parseObject(jsonObject.getString("comment")).getString("updatedDate").trim();
                if(isNeedToRunUnitTest(bipr,text,updatedDate)){
                    result=true;
                    break;
                }
            }
        }
        return result;
    }

    /**
     * 拿cookie，权限验证
     */
    private void getBitBucketCookie() throws IOException {
        RequestBody requestBody = new FormBody.Builder()
                .add("j_username",userName)
                .add("j_password",passWord)
                .add("_atl_remember_me","on")
                .add("submit","登录")
                .add("scan","企业微信扫码登录")
                .build();
        Request request = new Request.Builder()
                .url("https://code.fineres.com/j_atl_security_check")
                .addHeader("Cookie","SPC-SELECTED-CATEGORY-pg2=all; SPC-SELECTED-CATEGORY-PG2=67; SPC-SELECTED-CATEGORY-JSY=all; SPC-SELECTED-CATEGORY-DEC=all; SPC-SELECTED-CATEGORY-BUSSINESS=all; _ga=GA1.2.145599097.1623144057; SPC-SELECTED-CATEGORY-CORE=all; SPC-SELECTED-CATEGORY=18; BITBUCKETSESSIONID="+getSessionID())
                .post(requestBody)
                .build();
        Response response = client.newCall(request).execute();
        String cookie = response.header("Set-Cookie");
        System.out.println(cookie);
        if (StringUtils.isNotEmpty(cookie) && cookie.contains("_atl_bitbucket_remember_me") && response.code()==302){
            BitBucketUtils.cookie = cookie.split(";")[0];
        }
        response.close();
    }

    /**
     * 获取token需要用logout获取session*
     * @return sessionid
     */
    private String getSessionID() throws IOException {
        Request request = new Request.Builder()
                .url("https://code.fineres.com/logout")
                .build();
        Response response = client.newCall(request).execute();
        String cookie = response.header("Set-Cookie");
        response.close();
        if (StringUtils.isNotEmpty(cookie) && cookie.contains("BITBUCKETSESSIONID") && response.code()==200){
            return cookie.split("BITBUCKETSESSIONID=")[1].split(";")[0];
        }
        return null;
    }

    /**
     * 获取某一条pr的详细信息*
     * @param bipr 想获取信息的pr
     * @return 请求返回值
     */
    private String getPrResponse(BIPR bipr) throws Exception {
        String url = baseUrl + "/rest/api/latest/projects/" +
                bipr.getFatherRepository() + "/repos/" +
                bipr.getRepository() + "/pull-requests/" +
                bipr.getPrId() + "/activities";
        return getGetResponse(url);
    }

    /**
     * 任意get请求*
     * @param url url
     * @return 返回值
     */
    private String getGetResponse(String url) {
        Request request = new Request.Builder()
                .addHeader("Cookie",cookie)
                .url(url)
                .build();
        Response response = null;
        try {
            response = client.newCall(request).execute();
            System.out.println("url="+url);
            if (response.code()!=200){
                return "";
            }
            System.out.println("response code= "+response.code());
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
        }finally {
            if (Objects.nonNull(response))
                response.close();
        }
    }

    public String getPostResponseWithJson(String url,JSONObject jsonObject){
        RequestBody body = RequestBody.create(jsonObject.toString(),JSON_BODY);
        Request request = new Request.Builder()
                .addHeader("Content-Type","application/json")
                .addHeader("Cookie",cookie)
                .addHeader("Referer","https://code.fineres.com/projects/BUSSINESS/repos/nuclear-spider-adapter/pull-requests/10287/overview")
                .url(url)
                .post(body)
                .build();
        Response response = null;
        try {
            response = followRedirectClient.newCall(request).execute();
            System.out.println("url="+url);
            if (Objects.isNull(response.body())) {
                response.close();
                return "";
            } else {
                System.out.println("response code= "+response.code());
                String responseBody = Objects.requireNonNull(response.body()).string();
                response.close();
                return responseBody;
            }
        } catch (IOException e) {
            System.out.println(e.getMessage());
            return "";
        }finally {
            if (Objects.nonNull(response))
                response.close();
        }
    }

    /**
     * 判断字符串是不是一个非空的可以转化为int或long的数字
     * @param s 输入的字符串
     * @return 返回true或者false
     */
    private boolean isNotNumber(String s){
        //return !com.mysql.jdbc.StringUtils.isStrictlyNumeric(s) || (com.mysql.jdbc.StringUtils.isNullOrEmpty(s));
        return false;
    }


}

