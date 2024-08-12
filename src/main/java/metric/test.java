package metric;

import com.jcraft.jsch.SftpException;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.sql.SQLException;

public class test {
    public static void main(String[] args) throws IOException, SQLException {
        System.out.println("117.84.217.22".split(":")[0]);

        //MetricParser merMetricParser = new MetricParser("/Users/sunmuchao/Downloads/smc/86b213ce7f6f7efb.metric");
        //merMetricParser.parse();
        File file = new File("/Users/sunmuchao/Downloads/smc/aa");
        BufferedReader reader = null;
        try {
            System.out.println("以行为单位读取文件内容，一次读一整行：");
            reader = new BufferedReader(new FileReader(file));
            String tempString = null;
            int line = 1;
            // 一次读入一行，直到读入null为文件结束
            while ((tempString = reader.readLine()) != null) {
                String traceid = tempString.split("\"traceId\":\"")[1].split("\"")[0];
                System.out.println(traceid);
            }
            reader.close();
        } catch (IOException e) {
            e.printStackTrace();
        } finally {
            if (reader != null) {
                try {
                    reader.close();
                } catch (IOException e1) {
                }
            }
        }

    }
}
