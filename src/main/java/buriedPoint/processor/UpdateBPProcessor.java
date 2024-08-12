
package buriedPoint.processor;

import buriedPoint.BugPusher;
import buriedPoint.DBUtils;
import buriedPoint.Temporary;
import buriedPoint.executor.DataFlowExecutor;
import buriedPoint.executor.Executor;
import buriedPoint.executor.QueryExecutor;
import buriedPoint.point.BuriedPoint;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.net.URL;
import java.net.URLConnection;

public class UpdateBPProcessor extends BPProcessor {
    private DBUtils dbUtils;
    private String traceid;
    private BuriedPoint buriedPoint;
    private String cookie;

    public UpdateBPProcessor(BuriedPoint buriedPoint, DBUtils dbUtils, String traceid, String cookie) {
        super(buriedPoint, dbUtils, traceid, cookie);
        this.buriedPoint = buriedPoint;
        this.dbUtils = dbUtils;
        this.traceid = traceid;
        this.cookie = cookie;
    }

    public void process() throws Exception {
        if (judgeDuplicateBug()) {

        } else {
            int x = 0;
            //y=0代表问题均是已知或者非九数云问题
            int y = 0;
            BugPusher bugPusher = new BugPusher(cookie, buriedPoint, traceid, dbUtils);
            for (Executor executor : buriedPoint.Executors) {
                if (executor.getClass().getName().contains("QueryExecutor")) {
                    buriedPoint.addTotalExecutetime(((QueryExecutor) executor).getqueryExecutorTime());
                    if (((QueryExecutor) executor).getqueryExecutorTime() >= 1000000) {
                        if (bugPusher.addResult(((QueryExecutor) executor))) {
                            executor.isProblem = false;
                            x++;
                        }
                    } else {
                        executor.isProblem = false;
                        x++;
                    }
                } else if (executor.getClass().getName().contains("DataFlowExecutor")) {
                    buriedPoint.addTotalExecutetime(((DataFlowExecutor) executor).getDataFlowExecutorTime());
                    if (((DataFlowExecutor) executor).getDataFlowExecutorTime() >= 1000000) {
                        if (bugPusher.addUpdateResult(((DataFlowExecutor) executor))) {
                            executor.isProblem = false;
                            x++;
                        }
                    } else {
                        executor.isProblem = false;
                        x++;
                    }
                }

                if (executor.getQueueTime() >= 1000000) {
                    y++;
                    //判断是否是引擎外部排队导致
                    dbUtils.resIntoDB(traceid, "九数云Queue大于1s", 0, "jsyUpdate");
                }
            }

            //如果x!=executor代表存在引擎问题
            //如果y!=0代表已知问题:例如队列排队
            if (x != buriedPoint.Executors.size() && (Temporary.isbug == 1 || Temporary.isbug == 2)) {
                Temporary.setIsBug(2);
                if (!bugPusher.interrupt) {
                    bugPusher.pushBug(traceid, dbUtils);
                    System.out.println("推送bug");
                }
            }

            if (x == buriedPoint.Executors.size() &&
                    buriedPoint.getTotalTime() * 1000000 - buriedPoint.getTotalExecutetime() > 1000000 &&
                    buriedPoint.getTotalTime() * 1000000 - buriedPoint.getTotalExecutetime() > buriedPoint.getTotalTime() * 0.1
            ) {
                System.out.println("九数云问题");
                dbUtils.resIntoDB(traceid, "九数云问题", 0, "jsyUpdate");
            }
        }

    }

    private void downfile(String url, File saveDir, String d, String name) throws IOException {
        URLConnection conn = new URL(url).openConnection();
        conn.setRequestProperty("cookie", cookie);
        conn.setConnectTimeout(360 * 1000);
        InputStream InputStream = conn.getInputStream();
        byte[] getData = readInputStream(InputStream);
        File file = new File(saveDir + File.separator + d + "." + name);
        FileOutputStream fos = new FileOutputStream(file);
        fos.write(getData);
        if (fos != null) {
            fos.close();
        }
        if (InputStream != null) {
            InputStream.close();
        }
    }

    public static byte[] readInputStream(InputStream inputStream) throws IOException {
        byte[] buffer = new byte[1024];
        int len = 0;
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        try {
            while ((len = inputStream.read(buffer)) != -1) {
                bos.write(buffer, 0, len);
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
        bos.close();
        return bos.toByteArray();
    }
}
