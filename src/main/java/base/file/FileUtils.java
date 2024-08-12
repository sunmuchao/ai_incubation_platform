package base.file;

import com.jcraft.jsch.SftpException;

import java.io.*;

public class FileUtils {
    public void write(String fileName) throws SftpException {

    }


    /**
     * 替换文件中指定字符串*
     * @param filepath 文件
     * @param oldStr 要替换的字符
     * @param replaceStr 替换为什么字符
     */
    public static void iteratorDirectory(String filepath,String oldStr,String replaceStr) {
        File file = new File(filepath);
        if (file.isDirectory()) {
            String[] fileList =  file.list();
            if (fileList==null){
                System.out.println("文件"+filepath+"为空");
                return;
            }
            for (String s : fileList) {
                iteratorDirectory(filepath + "\\" + s, oldStr, replaceStr);
            }
        }else {
            replaceTxtByStr(filepath,oldStr,replaceStr);
        }
    }
    private static void replaceTxtByStr(String path,String oldStr,String replaceStr) {
        String temp = "";
        int len = oldStr.length();
        StringBuilder tempBuf = new StringBuilder();
        try {
            File file = new File(path);
            FileInputStream fis = new FileInputStream(file);
            InputStreamReader isr = new InputStreamReader(fis);
            BufferedReader br = new BufferedReader(isr);
            StringBuilder buf = new StringBuilder();

            while((temp = br.readLine()) != null) {
                if(temp.contains(oldStr)) {
                    int index = temp.indexOf(oldStr);
                    tempBuf.append(temp);
                    tempBuf.replace(index, index+len, replaceStr);
                    buf.append(tempBuf);
                    tempBuf.setLength(0);
                }else {
                    buf.append(temp);
                }
                buf.append(System.getProperty("line.separator"));

            }
            br.close();
            FileOutputStream fos = new FileOutputStream(file);
            PrintWriter pw = new PrintWriter(fos);
            pw.write(buf.toString().toCharArray());
            pw.flush();
            pw.close();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

}
