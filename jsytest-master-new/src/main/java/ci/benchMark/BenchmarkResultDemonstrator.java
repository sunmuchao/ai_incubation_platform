package ci.benchMark;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.PrintStream;
import java.lang.reflect.Field;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * @author sunmuchao
 * @date 2024/5/17 10:16 上午
 */

//结果展示器：用于对处理后的结果，进行展示生成结果报告
public class BenchmarkResultDemonstrator {
    Path workPath;

    BenchmarkResultDemonstrator(Path workPath){
        this.workPath = workPath;
    }

    public void process() throws FileNotFoundException {
        generateResultReport();
    }

    public void generateResultReport() throws FileNotFoundException {
        //html写入到文件中
        long timestamp = System.currentTimeMillis();
        String reportName = timestamp + ".html";
        System.out.println("生成结果报告名:" + reportName);
        StringBuilder stringHtml = new StringBuilder();
        String htmlPath = String.valueOf(workPath.resolve("html").resolve(reportName));
        File resultReport = new File(htmlPath);
        PrintStream printStream = new PrintStream(new FileOutputStream(resultReport));

        stringHtml = addReportHeader(stringHtml);
        stringHtml = addPerformanceRiseResult(stringHtml);
        stringHtml = addPerformanceReduceResult(stringHtml);
        stringHtml = addPerformanceFailResult(stringHtml);
        stringHtml = addNewAddedResult(stringHtml);


        //将HTML文件内容写入文件中
        printStream.println(stringHtml.toString());
    }

    public StringBuilder addReportHeader(StringBuilder stringHtml) {
        //输入HTML文件内容
        stringHtml.append("<html><head><meta http-equiv=\"Content-Type\" content=\"text/html; " +
                "charset=UTF-8\"><title>BenchMark测试报告</title></head><body><div></div>");
        stringHtml.append("<h2><font color=\"red\">说明: benchmark比较策略: 只跟当前分支进行比较, 性能提升的标准是跟三个历史pr比较均有提升</font></p></h2>");
        stringHtml.append("<h2><font color=\"red\">性能下降的标准是跟最近的一份历史pr进行比较性能下降</font></p></h2>");
        stringHtml.append("<body>");
        return stringHtml;
    }

    private StringBuilder addPerformanceRiseResult(StringBuilder stringHtml) {
        Set<BenchmarkResultComponent2> allPerformanceRiseCase = BenchmarkResultSet.getAllPerformanceRiseCase();
        for(BenchmarkResultComponent2 brc2 : allPerformanceRiseCase){
            stringHtml.append("<h2>性能上升</h2>");
            stringHtml.append("<table><thead><tr>");
            stringHtml.append("<th>caseName</th>");
            List<String> allFiledNames = getBenchmarkResultItemFieldNames();
            for(String fieldName : allFiledNames){
                stringHtml.append("<th>" + fieldName + "</th>");
            }
            stringHtml.append("</tr></thead>");
            stringHtml.append("<tbody><tr>");
            stringHtml.append("<td>" + brc2.getCaseName() + "</td>");
            for(String fieldName : allFiledNames){
                stringHtml.append("<td>" + brc2.getA().acquireGetField(fieldName) + "</td>");
            }

            for(BenchmarkResultItem bri : brc2.getB()){
                stringHtml.append("</tr><tr>");
                stringHtml.append("<td>" + brc2.getCaseName() + "</td>");
                for(String fieldName : allFiledNames){
                    stringHtml.append("<td>" + bri.acquireGetField(fieldName) + "</td>");
                }
            }
            stringHtml.append("</tr></tbody></table></body>");
        }
        return stringHtml;
    }

    private StringBuilder addPerformanceReduceResult(StringBuilder stringHtml) {
        Set<BenchmarkResultComponent2> allPerformanceRiseCase = BenchmarkResultSet.getAllPerformanceReduceCase();
        for(BenchmarkResultComponent2 brc2 : allPerformanceRiseCase){
            stringHtml.append("<h2>性能下降</h2>");
            stringHtml.append("<table><thead><tr>");
            stringHtml.append("<th>caseName</th>");
            List<String> allFiledNames = getBenchmarkResultItemFieldNames();
            for(String fieldName : allFiledNames){
                stringHtml.append("<th>" + fieldName + "</th>");
            }
            stringHtml.append("</tr></thead>");
            stringHtml.append("<tbody><tr>");
            stringHtml.append("<td>" + brc2.getCaseName() + "</td>");
            for(String fieldName : allFiledNames){
                stringHtml.append("<td>" + brc2.getA().acquireGetField(fieldName) + "</td>");
            }

            for(BenchmarkResultItem bri : brc2.getB()){
                stringHtml.append("</tr><tr>");
                stringHtml.append("<td>" + brc2.getCaseName() + "</td>");
                for(String fieldName : allFiledNames){
                    stringHtml.append("<td>" + bri.acquireGetField(fieldName) + "</td>");
                }
            }
            stringHtml.append("</tr></tbody></table></body>");
        }
        return stringHtml;
    }

    private StringBuilder addPerformanceFailResult(StringBuilder stringHtml) {
        Set<BenchmarkResultComponent2> allPerformanceRiseCase = BenchmarkResultSet.getAllPerformanceFailCase();
        for(BenchmarkResultComponent2 brc2 : allPerformanceRiseCase){
            stringHtml.append("<h2>失败</h2>");
            stringHtml.append("<table><thead><tr>");
            stringHtml.append("<th>caseName</th>");
            List<String> allFiledNames = getBenchmarkResultItemFieldNames();
            for(String fieldName : allFiledNames){
                stringHtml.append("<th>" + fieldName + "</th>");
            }
            stringHtml.append("</tr></thead>");
            stringHtml.append("<tbody><tr>");
            stringHtml.append("<td>" + brc2.getCaseName() + "</td>");
            for(String fieldName : allFiledNames){
                stringHtml.append("<td>" + brc2.getA().acquireGetField(fieldName) + "</td>");
            }

            stringHtml.append("</tr></tbody></table></body>");
        }
        return stringHtml;
    }

    private StringBuilder addNewAddedResult(StringBuilder stringHtml) {
        Set<BenchmarkResultComponent2> allPerformanceRiseCase = BenchmarkResultSet.getAllNewAddedCase();
        for(BenchmarkResultComponent2 brc2 : allPerformanceRiseCase){
            stringHtml.append("<h2>新增</h2>");
            stringHtml.append("<table><thead><tr>");
            stringHtml.append("<th>caseName</th>");
            List<String> allFiledNames = getBenchmarkResultItemFieldNames();
            for(String fieldName : allFiledNames){
                stringHtml.append("<th>" + fieldName + "</th>");
            }
            stringHtml.append("</tr></thead>");
            stringHtml.append("<tbody><tr>");
            stringHtml.append("<td>" + brc2.getCaseName() + "</td>");
            for(String fieldName : allFiledNames){
                stringHtml.append("<td>" + brc2.getA().acquireGetField(fieldName) + "</td>");
            }

            stringHtml.append("</tr></tbody></table></body>");
        }
        return stringHtml;
    }

    public List<String> getBenchmarkResultItemFieldNames(){
        Class<?> clazz = ci.benchMark.BenchmarkResultItem.class;
        List<String> fieldNames = new ArrayList<>();

        // 使用反射获取类中声明的所有字段
        Field[] fields = clazz.getDeclaredFields();

        // 遍历字段数组，获取字段名并加入列表
        for (Field field : fields) {
            fieldNames.add(field.getName());
        }

        return fieldNames;
    }
}
