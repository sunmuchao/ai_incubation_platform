/**
 * @author sunmuchao
 * @date 2023/9/7 10:05 上午
 */

import java.io.BufferedReader;
import java.io.File;
import java.io.FileWriter;
import java.io.InputStreamReader;
import java.io.PrintWriter;

public class DynamicClassCreationAndExecution {
    public static void main(String[] args) throws Exception {
        // 定义类名和类内容
        String className = "EnsureTableSpaceTest";
        String classContent = "public class EnsureTableSpaceTest {\n" +
                "    public static void main(String[] args) throws Exception {\n" +
                "        System.out.println(\"yes\");\n" +
                "    }\n" +
                "}";

        // 将类内容写入.java文件
        String fileName = className + ".java";
        FileWriter fileWriter = new FileWriter(fileName);
        PrintWriter printWriter = new PrintWriter(fileWriter);
        printWriter.println(classContent);
        printWriter.close();

        // 编译生成的Java文件
        Process compileProcess = Runtime.getRuntime().exec("javac " + fileName);
        int compileExitCode = compileProcess.waitFor();

        if (compileExitCode == 0) {
            // 编译成功，执行类的main方法
            Process executeProcess = Runtime.getRuntime().exec("java " + className);
            int executeExitCode = executeProcess.waitFor();
            BufferedReader br = new BufferedReader(new InputStreamReader(executeProcess.getInputStream()));
            String line;
            while((line = br.readLine()) != null){
                System.out.println(line);
            }
            if (executeExitCode == 0) {
                System.out.println("类的main方法执行成功");
            } else {
                System.err.println("类的main方法执行失败");
            }
        } else {
            System.err.println("编译失败");
        }

        // 清理生成的文件（可选）
        File generatedFile = new File(fileName);
        generatedFile.delete();
    }
}

