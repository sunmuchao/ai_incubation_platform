package ci.bi.unitTest;

import base.http.JSchUtil;
import cn.hutool.core.io.FileUtil;
import cn.hutool.core.io.file.FileReader;
import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.google.common.base.Preconditions;
import com.jcraft.jsch.JSchException;
import org.apache.commons.lang3.StringUtils;

import java.io.IOException;
import java.nio.charset.Charset;
import java.util.*;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

public class BIPreTest {

    private static final String repositoryFile = Optional.ofNullable(System.getProperty("repositoryFile")).orElse("");
    protected static final Map<String,String> repositories = new HashMap<>();
    protected static final Map<String,String> testRepositories = new HashMap<>();
    private static final BitBucketUtils bitBucketUtils = BitBucketUtils.getInstance().refreshCookie();

    static {
        //获取配置文件中所有仓库和主仓库
        Preconditions.checkArgument(FileUtil.isFile(repositoryFile),"file "+repositoryFile+" not exist!");
        FileReader fileReader = new FileReader(repositoryFile, Charset.defaultCharset());
        for (String repository:fileReader.readLines()){
            if (!StringUtils.isNotEmpty(repository) || !repository.contains(" ")){
                continue;
            }
            if (repository.startsWith("#")){
                //todo 后续看下注释后有没有啥更好的逻辑可以用
//                String s = repository.split("#")[1];
//                testRepositories.put(s.split(" ")[0],s.split(" ")[1]);
            }else {
                repositories.put(repository.split(" ")[0],repository.split(" ")[1]);
                testRepositories.put(repository.split(" ")[0],repository.split(" ")[1]);
            }
        }
    }

    /**
     * 启动pr单测*
     * @param bipr 要进行单测的pr,并且确保主仓库是放在第一位的
     */
    private static void startPrUnitTest(BIPR bipr) throws Exception {
        System.out.println("start run FatherRepository:"+bipr.getFatherRepository()+"  Repository:"+bipr.getRepository()+"  prid:"+bipr.getPrId()+" needToRunAll:"+bipr.isNeedToRunAll());
        List<BIPR> unionPrs = new ArrayList<>();
        unionPrs.add(bipr);
        if (Objects.nonNull(bipr.getUnionFactory())){
            //联合单测的将所需pr和仓库储存
            for (Map.Entry<String, String> next : bipr.getUnionFactory().entrySet()) {
                String repository = next.getKey();
                BIPR biPr = new BIPR(repository, repositories.get(repository), next.getValue());
                unionPrs.add(biPr);
            }
        }

        //拿到所有的patch
        StringBuilder patchRepositories = new StringBuilder();
        for (BIPR biPr:unionPrs){
            bitBucketUtils.downloadPatch(biPr);
            patchRepositories.append(biPr.getRepository()).append(":").append(biPr.getPrId()).append(",");
        }
        patchRepositories.deleteCharAt(patchRepositories.length()-1);

        //判断是否需要run全部
        StringBuilder repository = new StringBuilder();
        if (bipr.isNeedToRunAll()){
            for (Map.Entry<String, String> next : testRepositories.entrySet()) {
                repository.append(next.getKey()).append(",");
            }
        }else {
            for (BIPR biPr:unionPrs){
                repository.append(biPr.getRepository()).append(",");
            }
        }
        repository.deleteCharAt(repository.length()-1);

        //判断子模块
        StringBuilder subModules = new StringBuilder("null");
        if (Objects.nonNull(bipr.getSubModules())){
            subModules = new StringBuilder();
            for (String subModule : bipr.getSubModules()) {
                subModules.append(subModule).append(",");
            }
            subModules.deleteCharAt(subModules.length() - 1);
        }

        //开始调用脚本
        JSchUtil jSchUtil = new JSchUtil();
        try {
            jSchUtil.initializeSession("root","192.168.5.10","Yunzx@123");
            System.out.println(jSchUtil.execQuery("python3 /opt/BITest/jenkins_api.py 6.0-bi-unit-test "+repository+" "+patchRepositories+" "+bipr.getBuilder()+" release/6.0 "+subModules));
        } catch (JSchException e) {
            e.printStackTrace();
        }finally {
            jSchUtil.closeSession();
            System.out.println("结束");
        }
    }


    /**
     * 获取所有的需要执行的pr*
     * @param repository 仓库名
     * @param fatherRepository 父仓库名
     * @return 需要执行的pr的列表
     */
    private static List<BIPR> getPr(String repository,String fatherRepository) throws Exception {
        String prListResponse = bitBucketUtils.getPrListResponse(repository, fatherRepository);
 //       if (Objects.isNull(prListResponse) || prListResponse.isEmpty()) return new ArrayList<>();
        if (Objects.isNull(prListResponse) ) return new ArrayList<>();
        List<BIPR> prList = new ArrayList<>();
        JSONArray jsonArray;
        try{
            jsonArray=JSON.parseArray(prListResponse.split("initialData")[1].split("\"values\":")[1].split(",\"start\":")[0]);
        }catch (Exception e){
            return new ArrayList<>();
        }
        for (int i=0;i< jsonArray.size();i++){
            JSONObject jsonObject = jsonArray.getJSONObject(i);
            String displayId = ((JSONObject) JSON.parse(jsonObject.getString("toRef"))).getString("displayId");
            //控制release
            if (!displayId.contains("release")) continue;
            BIPR bipr = new BIPR(((JSONObject) JSON.parse(jsonObject.getString("toRef"))).getString("displayId"),
                    ((JSONObject) JSON.parse(((JSONObject) (JSON.parse(jsonObject.getString("author")))).getString("user"))).getString("name"),
                    jsonObject.getString("id"),
                    repository,fatherRepository);
            bipr.setUpdatedDatelong(jsonObject.getString("updatedDate"));
            bipr.setState(jsonObject.getString("state"));
            if (bitBucketUtils.isNeedToTrigger(bipr)){
                prList.add(bipr);
            }
        }
        return prList;
    }

    public static void main(String[] args) throws IOException {
        Runnable runnable = () -> {
            try {
                System.out.println("开始运行一次 "+System.currentTimeMillis());
                bitBucketUtils.refreshCookie();
                for (Map.Entry<String, String> next : repositories.entrySet()) {
                    List<BIPR> prList = getPr(next.getKey(), next.getValue());
                    if (prList.size() > 0){
                        for (BIPR pr:prList) {
                            System.out.println("startPrUnitTest");
                            startPrUnitTest(pr);
                        }
                    }
                }
            } catch (Exception e) {
                System.out.println(e.getMessage());
            }

        };
        ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();
        scheduler.scheduleAtFixedRate(runnable, 0, 15, TimeUnit.SECONDS);


    }
}
