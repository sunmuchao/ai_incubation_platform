package ci.benchMark;

import base.http.JSchUtil;
import com.jcraft.jsch.JSchException;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.IOException;
import java.io.InputStream;
import java.net.URL;
import java.net.URLConnection;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import base.config.Application;

import static buriedPoint.processor.OperatorsPageBPProcessor.readInputStream;

public class SuiteUtil {
    private static int sleepTime = 0;
    private static String suitePath = BanchMarckParser.curpath + "suite/";
    private static JSchUtil jSchUtil;
    private static String cdCurPath = "cd " + BanchMarckParser.curpath + ";";

    public SuiteUtil() {
        jSchUtil = new JSchUtil();
        try {
            jSchUtil.initializeSession("root", "192.168.5.94", "polars");
        } catch (JSchException e) {
            e.printStackTrace();
        }
    }

    public void importSuiteToBenchmark(String url, String dirName, String benchmarkPath) throws IOException, InterruptedException {
        //先在本地解析一下，如果是大文件直接在22上下载
        String taskName = url.split("/")[url.split("/").length - 1].split("\\.")[0];
        //异步打断
        String line = null;
        downfile(url, new File(Application.workPath), taskName, "suite");

        BufferedReader reader = new BufferedReader(new FileReader(Application.workPath + "/" + taskName + ".suite"));
        line = reader.readLine();
        System.out.println("suite的第一行:" + line);
        if (line.contains("can't find table") || line.contains("Decision Server timeout!")) {
            System.out.println("表已被删除");
            return;
        } else if (line.contains("is exporting ahead of you, try later!")) {
            sleepTime += 5000;
            System.out.println("睡眠时间 = " + sleepTime);
            Thread.sleep(sleepTime);
            importSuiteToBenchmark(url, dirName, benchmarkPath);
            return;
        } else if (line.contains("data file is to large"))
            url = "https://qfx30.oss-cn-hangzhou.aliyuncs.com/qfx3/WEB-INF/polars/suite/" + taskName + ".suite2";

        asynUpoad(benchmarkPath, url, dirName);
        //手动导入
        //jSchUtil.execQuery("cd /data/ContinuousIntegration/polars_test-benchmark &&" + "./prepare.sh && ./prepare_dict.sh && ./genDictionary.sh");
    }

    public static void asynUpoad(String benchmarkPath, String url, String dirName) {
        JSchUtil jSchUtil = new JSchUtil();
        Thread thread = new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    jSchUtil.initializeSession("root", "192.168.5.94", "polars");
                    jSchUtil.execQuery(
                            "cd " + benchmarkPath + " && " +
                                    "curl -H 'authorization:Bearer " + Application.fine_auth_token +
                                    "' --url '" + url + "'" +
                                    " --output '" + dirName + ".suite2' && cd .."
                    );
                } catch (JSchException e) {
                    e.printStackTrace();
                }
            }
        });
        thread.start();
    }

    private void downfile(String url, File saveDir, String d, String name) throws IOException {
        URLConnection conn = new URL(url).openConnection();
        conn.setRequestProperty("cookie", Application.jsyCookie);
        conn.setConnectTimeout(360 * 1000);
        InputStream InputStream = conn.getInputStream();
        byte[] getData = readInputStream(InputStream);
        File file = new File(saveDir + "/" + File.separator + d + "." + name);
        FileOutputStream fos = new FileOutputStream(file);
        fos.write(getData);
        if (fos != null) {
            fos.close();
        }
        if (InputStream != null) {
            InputStream.close();
        }
    }
}
