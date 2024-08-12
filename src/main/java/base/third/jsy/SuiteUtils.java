package base.third.jsy;

import base.http.JSchUtil;
import cn.hutool.core.io.FileUtil;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.ResponseBody;
import org.apache.log4j.Logger;

import java.io.*;

public class SuiteUtils {
    private static final Logger logger = Logger.getLogger(SuiteUtils.class);
    private final OkHttpClient client;
    private final JSchUtil jSchUtil;

    public SuiteUtils(OkHttpClient client,JSchUtil jSchUtil) {
        this.client = client;
        this.jSchUtil = jSchUtil;
    }


    public OkHttpClient getClient() {
        return client;
    }

    public void importSuiteToBenchmark(String url, String taskName, String saveDir, String name,String fineAuthToken) throws IOException, InterruptedException {
        String filePath = saveDir + "/" + name;
        downfile(url, saveDir, name, fineAuthToken);
        logger.info("下载完成,地址为:"+filePath);
        BufferedReader reader = new BufferedReader(new FileReader(filePath));
        String line = reader.readLine();
        logger.info("suite的第一行:" + line);
        if (line.contains("is exporting ahead of you, try later!")) {
            Thread.sleep(15000);
            importSuiteToBenchmark(url,taskName, saveDir, name,fineAuthToken);
        } else if (line.contains("data file is to large")){
            url = "https://qfx30.oss-cn-hangzhou.aliyuncs.com/qfx3/WEB-INF/polars/suite/" + taskName + ".suite2";
            if (FileUtil.exist(filePath)){
                logger.info(filePath + "重复，删除之前的");
                FileUtil.del(filePath);
            }
            jSchUtil.execQuery("wget -O " + filePath + " " + url);
//            importSuiteToBenchmark(url,taskName, saveDir, name,fineAuthToken);
        }else if (line.contains("not found")){
            logger.info(filePath+"无效,删除此suite");
            FileUtil.del(filePath);
        }else {
            if(!FileUtil.exist(filePath)){
                logger.info("下载suite超时,需要手动下载,url="+url);
            }
        }

    }


    private void downfile(String url, String saveDir, String name, String fineAuthToken){
        String cookie = "tenantId=7ad5219f-8342-4a1c-b6d6-51ea2b6ea2b6; fine_remember_login=-1; fr_id_appname=jiushuyun; fine_auth_token=" + fineAuthToken;
        File dir = new File(saveDir);
        if (!dir.exists()) {
            dir.mkdirs(); // 创建目录及其所有父目录
        }
        String filePath = saveDir + "/" + name;
        if (FileUtil.exist(filePath)){
            logger.info(filePath + "重复，删除之前的");
            FileUtil.del(filePath);
        }
        logger.info("开始从"+url+"下载suite");
        Request request = new Request.Builder()
                .url(url)
                .addHeader("cookie",cookie)
                .build();
        ResponseBody body = null;
        try {
            Response response = client.newCall(request).execute();

            body = response.body();
            InputStream inputStream = body != null ? body.byteStream() : null;
            BufferedInputStream bufferedInputStream = new BufferedInputStream(inputStream);
            FileOutputStream fileOutputStream = new FileOutputStream(filePath);
            int len;
            byte[] buffer = new byte[1024];
            while ((len = bufferedInputStream.read(buffer)) != -1) {
                fileOutputStream.write(buffer, 0, len);
            }
            fileOutputStream.flush();
            fileOutputStream.close();
            bufferedInputStream.close();
        } catch (IOException e) {
            logger.error(e.getMessage(),e);
        }finally {
            if (body != null) {
                body.close();
            }
        }
    }
}
