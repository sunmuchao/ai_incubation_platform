package base.cmd;

import ci.benchMark.PR;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;

/**
 * @author sunmuchao
 * @date 2023/11/15 5:29 下午
 */
public class ShellTool {
    /*public static String[] cmd(String cmd) throws Exception {
        System.out.println(cmd);
        Process proc = Runtime.getRuntime().exec(new String[]{"/bin/sh", "-c", cmd});
        proc.waitFor();
        System.out.println("Standard Output:");
        printOutput(proc.getInputStream());

        System.out.println("Error Output:");
        String err = readOutput(proc.getErrorStream());
        if (err != null && !err.equals("")) throw new Exception("获取测试文件信息失败:" + err);
        String[] out = err.split("\n");
        return out;
    }*/

    public static void cmd(String cmd) throws Exception {
        System.out.println(cmd);

        ProcessBuilder processBuilder = new ProcessBuilder("/bin/sh", "-c", cmd);
        processBuilder.redirectErrorStream(true);  // 将错误流重定向到输入流

        Process proc = processBuilder.start();

        // 设置单独的线程来读取和打印标准输出和错误
        Thread outputThread = new Thread(() -> { try { printOutput(proc.getInputStream()); } catch (IOException e) { e.printStackTrace(); } });
        outputThread.start();

        int exitCode = proc.waitFor();
        // 等待输出线程完成
        outputThread.join();

        if (exitCode != 0) {
            throw new Exception("获取测试文件信息失败。退出码：" + exitCode);
        }
    }


    private static String readOutput(InputStream inputStream) throws IOException {
        StringBuffer outputLines = new StringBuffer();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream))) {
            String line;
            while ((line = reader.readLine()) != null) {
                outputLines.append(line + "\n");
            }
        }
        return outputLines.toString();

    }

    private static String printOutput(InputStream inputStream) throws IOException {
        StringBuilder outputLines = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new InputStreamReader(inputStream))) {
            String line;
            while ((line = reader.readLine()) != null) {
                outputLines.append(line).append("\n");
                System.out.println(line);
            }
        }
        return outputLines.toString();
    }
}
