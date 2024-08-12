package ci.bi.unitTest;

import base.http.JSchUtil;
import com.alibaba.fastjson.JSONObject;
import com.jcraft.jsch.JSchException;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class AddBIComment {
    private static final Map<String,String> repositories = BIPreTest.repositories;
    private static final BitBucketUtils bitBucketUtils = BitBucketUtils.getInstance().refreshCookie();
    private static final JSchUtil jschUtil = new JSchUtil();
    private static final Map<String,String> resultMap = new HashMap<>();
    private static String repository = "";
    private static String reportFile = "";
    private static String prId = "";
    private static String buildUrl = "";
    private static String workSpace = "";

    public static void main(String[] args) {
        String patchRepositories = args[0].split(",")[0];
        repository = patchRepositories.split(":")[0];
        prId = patchRepositories.split(":")[1];
        reportFile = args[1];
        buildUrl = args[2];
        workSpace = args[3];
        int isEnd = Integer.parseInt(args[4]);
        if (isEnd >0){
            addEndComment();
        }else {
            addStartComment();
        }
    }

    private static void addStartComment(){
        sendComment("开始构建单测......"+"\n"+"构建界面:" + buildUrl);

    }

    private static void addEndComment(){
        try {
            jschUtil.initializeSession("root","192.168.5.10","Yunzx@123");
            List<String> list = jschUtil.execQueryList("cd "+workSpace+" && cat " + reportFile);
            if (!list.isEmpty()){
                for (String s : list){
                    if (s.startsWith("Failures")){
                        resultMap.put("Failures",s.trim().split(": ")[1]);
                    }else if (s.startsWith("Tests")){
                        resultMap.put("Tests",s.trim().split(": ")[1]);
                    }
                }
            }
        } catch (JSchException e) {
            e.printStackTrace();
        }finally {
            jschUtil.closeSession();
            System.out.println("结束");
        }
        System.out.println("开始构建请求体");
        if (resultMap.isEmpty()){
            sendComment("构建失败！" +"\n"
                    +"报告: "+buildUrl+"console");
        }else if (Integer.parseInt(resultMap.get("Failures")) ==0){
            sendComment("测试通过！" + "\n"
                    +"测试数量: "+resultMap.get("Tests"));
        }else {
            sendComment("测试失败！" + "\n"
                    +"测试数量: "+resultMap.get("Tests") +"\n"
                    + "测试失败数量:"+resultMap.get("Failures") + "\n"
                    +"报告:"+buildUrl+"testReport/");
        }
    }

    private static void sendComment(String text){
        System.out.println("开始构建请求");
        String fatherRepository = repositories.get(repository);
        String url = "https://code.fineres.com/rest/api/latest/projects/"+fatherRepository+"/repos/"+repository+"/pull-requests/"+prId+"/comments?diffType=EFFECTIVE&markup=true&avatarSize=48";
        JSONObject jsonObject = new JSONObject();
        jsonObject.put("text",text);
        jsonObject.put("severity","NORMAL");
        System.out.println("开始发送请求");
        System.out.println(bitBucketUtils.getPostResponseWithJson(url,jsonObject));
    }
}
