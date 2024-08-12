package buriedPoint;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;

public class GcValidator {
    public static Double gcTime(String addr, String startTime, String endTime) throws IOException {
        File gcfile = null;
        double gc = 0.0;
        String gcline, gcdate, gctime;
        //首先我拿到起始时间和结束时间，然后根据起始时间和结束时间
        if (addr.equals("polars191_6000")) {
            gcfile = new File("/Users/sunmuchao/Downloads/smc/polars191");
        } else if (addr.equals("polars193_6000"))
            gcfile = new File("/Users/sunmuchao/Downloads/smc/polars193");
        else if (addr.contains("109")) {
            gcfile = new File("/Users/sunmuchao/Downloads/smc/109");
        } else if (addr.contains("108")) {
            gcfile = new File("/Users/sunmuchao/Downloads/smc/108");
        }
        File[] fs = gcfile.listFiles();
        boolean meetLine = false;
        for (int a = 0; a < fs.length; a++) {
            BufferedReader gcreader = new BufferedReader(new FileReader(fs[a]));
            //获取startTime和endTime之间的内容 格式：2022-01-12T15:49:18
            //获取该行的时间字符串，如果比startTime小就读取下一行，否则就认为该行为startLine
            //如果该行比endTime大就认为该行为endLine，然后获取这两行之间的时间字符串进行相加，如果大于1s则认为gc有问题
            String startdate = startTime.split(" ")[0];
            String starttime = startTime.split(" ")[1];
            String endtime = endTime.split(" ")[1];
            while ((gcline = gcreader.readLine()) != null) {
                gcdate = gcline.substring(0, 10);
                gctime = gcline.substring(11, 19);
                if (gcdate.equals(startdate)) {
                    if (gctime.substring(0, 2).equals(starttime.substring(0, 2))) {
                        //分钟如果大于的话，就将当行设置为startLine
                        if (Integer.parseInt(gctime.substring(3, 5)) > Integer.parseInt(starttime.substring(3, 5))) {
                            meetLine = true;
                            //如果分钟相等的话，就判断秒
                        } else if (Integer.parseInt(gctime.substring(3, 5)) == Integer.parseInt(starttime.substring(3, 5))) {
                            if (Integer.parseInt(gctime.substring(6, 8)) >= Integer.parseInt(starttime.substring(6, 8))) {
                                meetLine = true;
                            }
                        }
                    }
                    if (gctime.substring(0, 2).equals(endtime.substring(0, 2))) {
                        //分钟如果大于的话，就将当行设置为endLine
                        if (Integer.parseInt(gctime.substring(3, 5)) > Integer.parseInt(endtime.substring(3, 5))) {
                            meetLine = false;
                            break;
                            //如果分钟相等的话，就判断秒
                        } else if (Integer.parseInt(gctime.substring(3, 5)) == Integer.parseInt(endtime.substring(3, 5))) {
                            if (Integer.parseInt(gctime.substring(6, 8)) >= Integer.parseInt(endtime.substring(6, 8))) {
                                meetLine = false;
                                break;
                            }
                        }
                    }
                    if (meetLine) {
                        String s = gcline.split("secs")[0];
                        gc += Double.parseDouble(s.split(",")[s.split(",").length - 1].trim());
                    }
                }
            }
        }
        return gc;
    }
}
