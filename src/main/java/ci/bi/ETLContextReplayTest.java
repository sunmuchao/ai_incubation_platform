package ci.bi;

import base.config.Application;
import base.file.FileUtils;
import base.http.JSchUtil;
//import com.mysql.jdbc.StringUtils;

import java.util.List;

/*public class ETLContextReplayTest {

    public static void main(String[] args) {
        if (args == null || args.length%3!=1){
            try {
                throw new Exception("参数数量不正确，程序不会运行！");
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        JSchUtil jSchUtil = Application.getBIJenkinsSessionInstance();
        if (jSchUtil==null){
            return;
        }
        try{
            int number=0;
            String basePath = args[number];
            while(number<args.length-1){
                String fileName = args[++number];
                String paraName = args[++number];
                String newValue = args[++number];
                String commend = "cd " + basePath + ";grep " + paraName + " " + fileName;
                System.out.println(commend);
                List<String> list = jSchUtil.execQueryList(commend);
                for (String s:list){
                    System.out.println(s);
                    if (!StringUtils.isEmptyOrWhitespaceOnly(s) && (s.contains(paraName+"=") || s.contains(paraName+" ="))){
                        System.out.println("查找到的匹配字符串为:"+s);
                        String oldValue = s.split("=")[1].split(";")[0];
         //               if (oldValue.contains("\"")) newValue="\""+newValue+"\"";
                        System.out.println("将为您替换"+oldValue+"为"+newValue+"");
                        FileUtils.iteratorDirectory(basePath+fileName,oldValue,newValue);
                    }
                }
            }
        }catch (Exception e){
            e.printStackTrace();
        }finally {
            jSchUtil.closeSession();
        }

    }
}
*/
