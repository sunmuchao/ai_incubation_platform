package ci.benchMark;

import base.db.JSYDBUtils;
import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.opencsv.CSVReader;

import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLConnection;
import java.util.*;
import java.util.stream.Collectors;

public class BanchMarckParser {
    //static String curpath = "/Users/sunmuchao/Downloads/benchmark/csv/";
    public static String curpath = "/data/ContinuousIntegration/polars_test-benchmark/";
    private static ArrayList<String> BaseLinePaths = new ArrayList<>();
    private static String strategypath = null;
    private static ArrayList<String> mergedPirds = new ArrayList<>();
    private static String mergedPrId = null;
    private static List<String> fallcaseList = new ArrayList<>();

    public static Map<String, Case> parseCSV(List<String> propers, String csvFile) {
        Map<String, Case> resSet = new LinkedHashMap();
        try {
            CSVReader reader = new CSVReader(new FileReader(csvFile));
            reader.readNext();
            String[] line;
            while ((line = reader.readNext()) != null) {
                Map<String, String> map = new HashMap();
                Case cs = new Case();
                for (int i = 0; i < (propers.size() - 1); i++) {
                    map.put(propers.get(i), line[i]);
                }

                cs.setUUID(map.get("runnerIp"), map.get("categoryName"), map.get("caseName"));
                cs.setFieldInfo(map.get("fieldInfo"));
                //               System.out.println(csvFile);
                //               System.out.println(map.get("warmCount"));
                if (Integer.valueOf(map.get("warmCount")) != 0)
                    cs.setAvgWarmTime(Long.valueOf(map.get("warmTime")) / Integer.valueOf(map.get("warmCount")));

                if (Integer.valueOf(map.get("measureCount")) != 0)
                    cs.setAvgMeasureTime(Long.valueOf(map.get("measureTime")) / Integer.valueOf(map.get("measureCount")));

                if (Integer.valueOf(map.get("conCount")) != 0)
                    cs.setAvgConTime(Long.valueOf(map.get("conTime")) / Integer.valueOf(map.get("conCount")));
                cs.setRealConMeasureSize((Integer.valueOf(map.get("conMeasureSize")) > Integer.valueOf(map.get("threadPoolSize"))) ?
                        Integer.valueOf(map.get("threadPoolSize")) : Integer.valueOf(map.get("conMeasureSize")));
                cs.setConFailedCount(Integer.valueOf(map.get("conFailedCount")));

                if (Integer.valueOf(map.get("measureGcCount")) != 0)
                    cs.setAvgMeasureGcTime(Long.valueOf(map.get("measureGcTime")) / Long.valueOf(map.get("measureGcCount")));

                if (Long.valueOf(map.get("measureJvmMemMax")) != 0)
                    cs.setMeasureJvmMemUsedMaxUsage(Long.valueOf(map.get("measureJvmMemUsedMax")) / Long.valueOf(map.get("measureJvmMemMax")));

                if (Long.valueOf(map.get("polarsMemMax")) != 0)
                    cs.setPolarsMemUsedMaxUsage(Long.valueOf(map.get("polarsMemUsedMax")) / Long.valueOf(map.get("polarsMemMax")));
                cs.setErrorInfo(map.get("errorInfo"));

                resSet.put(cs.getRunnerIp() + "_" + cs.getCategoryName() + "_" + cs.caseName, cs);
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
        return resSet;
    }

    //维护BanchMarck变量
    private static List<String> propers = new ArrayList();

    public static Map<String, List> getSlowCases(String baseLine, String Strategy) {

        Map<String, List> res = new LinkedHashMap();
        try {
            CSVReader csvReader = new CSVReader(new FileReader(Strategy));

            String[] firstLine;
            if ((firstLine = csvReader.readNext()) != null && propers.size() == 0) {
                for (String s : firstLine) {
                    propers.add(s);
                }
                propers.add("metric");
            }

            List<String> errList = new ArrayList();
            List<String> fallList = new ArrayList();
            List<String> upList = new ArrayList();
            List<String> LatestList = new ArrayList();
            List<String> normalList = new ArrayList();

            float avgScore = 0;
            float avgConScore = 0;

            Map<String, Case> StrategyResSet = parseCSV(propers, Strategy);

            Map<String, Case> baseLineResSet = parseCSV(propers, baseLine);

            /*Iterator<Map.Entry<Long, Case>> entries2 = baseLineResSet.entrySet().iterator();
            while (entries2.hasNext()) {
                System.out.println("策略:"+entries2.next().getKey());
            }*/

            //读取数据库中误错率
            //int allowErr = getallowErr();
            int allowErr = 13;
            for (String newUUID : StrategyResSet.keySet()) {
                int count = 0;
                for (String oldUUID : baseLineResSet.keySet()) {
                    boolean isNormal = true;
                    if (newUUID.equals(oldUUID)) {
                        Case oldCase = baseLineResSet.get(oldUUID);
                        Case newCase = StrategyResSet.get(newUUID);
                        //进行处理
                        //判断cpu数是否相等，如果不相等我们认为是环境导致的
                        if (oldCase.getCpuCount() != newCase.getCpuCount()) {
                            isNormal = false;
                            System.out.println("请检查cpu配额");
                        }

                        if (oldCase.getAvgMeasureTime() != 0 && newCase.getAvgMeasureTime() != 0 && oldCase.getAvgMeasureTime() < (100 - allowErr) / 100.00 * newCase.getAvgMeasureTime()
                                && Math.abs(newCase.getAvgMeasureTime() - oldCase.getAvgMeasureTime()) > 100) {
                            isNormal = false;
                            fallList.add(newUUID);
                            System.out.println("性能下降:" + newUUID);
                        }

                        if (oldCase.getAvgMeasureTime() != 0 && newCase.getAvgMeasureTime() != 0 && oldCase.getAvgMeasureTime() > (100 + allowErr) / 100.00 * newCase.getAvgMeasureTime()
                                && (100 - allowErr) / 100.00 * oldCase.getAvgMeasureTime() > 100 && Math.abs(newCase.getAvgMeasureTime() - oldCase.getAvgMeasureTime()) > 100) {
                            isNormal = false;
                            upList.add(newUUID);
                            System.out.println("性能优化:" + newUUID);
                        }

                        if (oldCase.getConFailedCount() < newCase.getConFailedCount() || !newCase.getErrorInfo().equals("") || newCase.getAvgMeasureTime() == 0) {
                            isNormal = false;
                            errList.add(newUUID);
                            System.out.println("失败的:" + newUUID);
                        }

                        if (isNormal)
                            normalList.add(newUUID);

                        if (oldCase.getAvgMeasureTime() != 0 && newCase.getAvgMeasureTime() != 0) {
                            double value = Math.max(oldCase.getAvgMeasureTime(), newCase.getAvgMeasureTime()) / Math.min(oldCase.getAvgMeasureTime(), newCase.getAvgMeasureTime()) - 1;
                            if (oldCase.getAvgMeasureTime() < newCase.getAvgMeasureTime()) value = -value;
                            avgScore += value;
                        } else if (oldCase.getAvgConTime() != 0 && newCase.getAvgConTime() != 0) {
                            double value = Math.max(oldCase.getAvgConTime(), newCase.getAvgConTime()) / Math.min(oldCase.getAvgConTime(), newCase.getAvgConTime()) - 1;
                            if (oldCase.getAvgConTime() < newCase.getAvgConTime()) value = -value;
                            avgConScore += value;
                        }
                        break;
                    }

                    if (++count == baseLineResSet.size()) {
                        //属于新增用例
                        LatestList.add(newUUID);
                    }
                }
            }
            List<Float> score = new ArrayList<>();
            score.add(avgScore / StrategyResSet.size());
            score.add(avgConScore / StrategyResSet.size());

            res.put("新增", LatestList);
            res.put("性能下降", fallList);
            res.put("性能提升", upList);
            res.put("错误", errList);
            res.put("性能无变化", normalList);
            //           System.out.println("============================score"+score);
            res.put("性能平均分", score);
            //           System.out.println("=====================结束了getSlowCases方法");
        } catch (IOException e) {
            e.printStackTrace();
        }
        return res;
    }


    public static boolean showResult(PR pr) throws IOException {
        System.out.println(curpath);
        boolean isMerge = false;

        try {
            //设置featurepath releasepath llvmpath
            PostProcessLatestMergedPrid(getLatestMergedPrid(), pr);

            LinkedHashSet errSet = new LinkedHashSet();
            LinkedHashSet upSet = new LinkedHashSet();
            LinkedHashSet fallSet = new LinkedHashSet();
            LinkedHashSet normalSet = new LinkedHashSet();
            LinkedHashSet latestSet = new LinkedHashSet();

            Map<String, LinkedHashSet> onlyPrintNewMap = new HashMap();
            Map<String, LinkedHashSet> PrintAllMap = new HashMap();

            ArrayList score = null;
            if (pr.getTask().getCodeTypes()[0].equals("java")) {
                strategypath = curpath + pr.getPrId() + "-" + pr.getTask().getDataTypes()[0] + ".csv";
            } else if (pr.getTask().getCodeTypes()[0].equals("c++")) {
                strategypath = curpath + pr.getPrId() + "-" + pr.getTask().getDataTypes()[0] + "_cpp.csv";
            }

            CustomHashMap upCustomHashMap = new CustomHashMap(BaseLinePaths.size());
            CustomHashMap latestCustomHashMap = new CustomHashMap(BaseLinePaths.size());

            System.out.println("======================BaseLinePaths.size()" + BaseLinePaths.size());
            for (int i = 0; i < BaseLinePaths.size(); i++) {
                System.out.println("比较的文件路径:" + BaseLinePaths.get(i));
                Map<String, List> resMap = getSlowCases(BaseLinePaths.get(i), strategypath);
                errSet.addAll((ArrayList) resMap.get("错误"));
                if (i == 0) {
                    System.out.println("BaseLinePaths(0)" + BaseLinePaths.get(i));
                    fallSet.addAll((ArrayList) resMap.get("性能下降"));
                }
                //upSet.addAll((ArrayList) resMap.get("性能提升"));
                //latestSet.addAll((ArrayList) resMap.get("新增"));
                upCustomHashMap.putAll(resMap.get("性能提升"));
                latestCustomHashMap.putAll(resMap.get("新增"));
                normalSet.addAll((ArrayList) resMap.get("性能无变化"));
                score = (ArrayList) resMap.get("性能平均分");
            }
            //性能提升取交集
            upSet.addAll(upCustomHashMap.getIntersection());
            //新增用例取交集
            latestSet.addAll(latestCustomHashMap.getIntersection());

            onlyPrintNewMap.put("新增", latestSet);
            onlyPrintNewMap.put("错误", errSet);

            PrintAllMap.put("性能下降", fallSet);
            PrintAllMap.put("性能提升", upSet);
            PrintAllMap.put("性能无变化", normalSet);

            //判断是否需要触发自动合入
            if (errSet.size() == 0 && latestSet.size() == 0) isMerge = true;

            StringBuilder stringHtml = new StringBuilder();
            int number = 1;
            //打开文件
            File file = null;
            if (pr.getTask().getCodeTypes()[0].equals("java")) {
                file = new File(curpath + "html/" + pr.getPrId() + "-" + pr.getTask().getDataTypes()[0] + "-" + number + ".html");
            } else if (pr.getTask().getCodeTypes()[0].equals("c++")) {
                file = new File(curpath + "html/" + pr.getPrId() + "-" + pr.getTask().getDataTypes()[0] + "-" + number + "_cpp.html");
            }
            while (file.exists()) {
                number += 1;
                if (pr.getTask().getCodeTypes()[0].equals("java")) {
                    file = new File(curpath + "html/" + pr.getPrId() + "-" + pr.getTask().getDataTypes()[0] + "-" + number + ".html");
                } else if (pr.getTask().getCodeTypes()[0].equals("c++")) {
                    file = new File(curpath + "html/" + pr.getPrId() + "-" + pr.getTask().getDataTypes()[0] + "-" + number + "_cpp.html");
                }
            }

            PrintStream printStream = new PrintStream(new FileOutputStream(file));

            //输入HTML文件内容
            stringHtml.append("<html><head><meta http-equiv=\"Content-Type\" content=\"text/html; " +
                    "charset=UTF-8\"><title>BenchMark测试报告</title></head><body><div></div>");


            //将csv文件放入到内存中
            Map<String, ArrayList> csvMap = new HashMap();
            csvMap.put("strategy", new ArrayList());

            for (int i = 0; i < mergedPirds.size(); i++)
                csvMap.put(pr.getDisplayId() + ":" + mergedPirds.get(i), new ArrayList());

            Map<String, CSVReader> readerMap = new HashMap();

            readerMap.put("strategy", new CSVReader(new FileReader(strategypath)));
            for (int i = 0; i < BaseLinePaths.size(); i++) {
                readerMap.put(pr.getDisplayId() + ":" + mergedPirds.get(i), new CSVReader(new FileReader(BaseLinePaths.get(i))));
            }

            String[] line;
            for (Map.Entry<String, CSVReader> reader : readerMap.entrySet()) {
                while ((line = reader.getValue().readNext()) != null) {
                    csvMap.get(reader.getKey()).add(line);
                }
            }
            stringHtml.append("<h2><font color=\"red\">说明: benchmark比较策略: 只跟当前分支进行比较, 性能提升的标准是跟三个历史pr比较均有提升</font></p></h2>");
            stringHtml.append("<h2><font color=\"red\">性能下降的标准是跟最近的一份历史pr进行比较性能下降</font></p></h2>");

            for (Map.Entry<String, LinkedHashSet> entry : onlyPrintNewMap.entrySet()) {
                String name = entry.getKey();
                Set<String> set = entry.getValue();
                Iterator iterator = set.iterator();
                if (!set.isEmpty() && !stringHtml.toString().contains(name + "用例"))
                    stringHtml.append("<table border=\"1\"><h2>" + name + "用例</h2><tr>");

                while (iterator.hasNext()) {
                    String UUID = (String) iterator.next();
                    try {
                        ArrayList<String[]> strategyList = csvMap.get("strategy");
                        for (int i = 0; i < strategyList.size(); i++) {
                            String[] l = strategyList.get(i);
                            if (String.valueOf(l[0] +"_" + l[1] + "_" + l[2]).equals(String.valueOf(UUID))) {
                                System.out.println(name + "列表：" + l[0] + l[1] + l[2]);

                                //stringHtml.append("<td bgcolor=\"#00FF00\">");
                                for (String s : propers)
                                    stringHtml.append("<td bgcolor=\"#00FF00\">" + s + "</td>\n");
                                stringHtml.append("</td>");
                                stringHtml.append("</tr><tr>\n");
//
//                                for (String s : l) stringHtml.append("<td>" + s + "</td>\n");
//                                stringHtml.append("<td>" + "这是一个metric" + "</td>\n");

                                String metricPath = MetricUtil.getMetric(l, propers, pr);
                                for (String s : l) stringHtml.append("<td>" + s + "</td>\n");
                                if (metricPath == null || metricPath.length() <= 0) {
                                    stringHtml.append("<td>" + "metric未获得，可联系Frank.Niu查看原因" + "</td>\n");
                                } else if (metricPath.contains("error")) {
                                    stringHtml.append("<td>" + metricPath + "</td>\n");
                                } else {
//                                stringHtml.append("<td>" + metrics.get(0) + "</td>\n");
                                    stringHtml.append("<td>" + "<a href=\"http://192.168.5.94:8082/" + metricPath + "\">下载metric</a></td>\n");
                                }


                                stringHtml.append("<td><a href=\"http://192.168.5.94:8082/pls/" + l[2] + "\">下载pls</a></td>\n");
                                stringHtml.append("<td><a href=\"http://192.168.5.94:8082/suite/" + l[2].split("\\.")[0] + ".suite2" + "\">下载suite</a></td></tr>\n");
                            }
                        }
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
            }

            for (Map.Entry<String, LinkedHashSet> entry : PrintAllMap.entrySet()) {
                String name = entry.getKey();
                Set<String> set = entry.getValue();
                Iterator iterator = set.iterator();
                if (!set.isEmpty() && !stringHtml.toString().contains(name + "用例"))
                    stringHtml.append("<table border=\"1\"><h2>" + name + "用例</h2><tr>");
                while (iterator.hasNext()) {
                    String UUID = (String) iterator.next();
                    ArrayList<String[]> strategyList = csvMap.get("strategy");
                    strategyList.forEach(l -> {
                        if (String.valueOf(l[0] +"_" + l[1] + "_" + l[2]).equals(String.valueOf(UUID))) {
                            System.out.println(name + "列表：" + l[0] + l[1] + l[2]);
                            stringHtml.append("<td bgcolor=\"#00FF00\">");
                            for (String s : propers) stringHtml.append("<td bgcolor=\"#00FF00\">" + s + "</td>\n");
                            stringHtml.append("</td>");
                            stringHtml.append("</tr><tr><td>" + "当前用例" + "</td>");

                            if ("性能下降".equals(name)) fallcaseList.add(l[2]);
//                            System.out.println("================进入了getMetric");
                            String metricPath = MetricUtil.getMetric(l, propers, pr);
                            for (String s : l) stringHtml.append("<td>" + s + "</td>\n");
                            if (metricPath == null || metricPath.length() <= 0) {
                                stringHtml.append("<td>" + "metric未获得，可联系Frank.Niu查看原因" + "</td>\n");
                            } else if (metricPath.contains("error")) {
                                stringHtml.append("<td>" + metricPath + "</td>\n");
                            } else {
//                                stringHtml.append("<td>" + metrics.get(0) + "</td>\n");
                                stringHtml.append("<td>" + "<a href=\"http://192.168.101.29:8082/" + metricPath + "\">下载metric</a></td>\n");
                            }
                            stringHtml.append("<td><a href=\"http://192.168.101.29:8082/pls/" + l[2] + "\">下载pls</a></td>\n");
                            stringHtml.append("<td><a href=\"http://192.168.101.29:8082/suite/" + l[2].split("\\.")[0] + ".suite2" + "\">下载suite</a></td></tr>\n");
                        }
                    });

                    ListIterator<Map.Entry<String, ArrayList>> li = new ArrayList(csvMap.entrySet()).listIterator(csvMap.size());

                    while (li.hasPrevious()) {
                        Map.Entry<String, ArrayList> entrySet = li.previous();
                        if (entrySet.getKey().equals("strategy")) continue;
                        ArrayList<String[]> lines = entrySet.getValue();
                        lines.forEach(l -> {
                            if (String.valueOf(l[0] +"_" + l[1] + "_" + l[2]).equals(String.valueOf(UUID))) {

                                stringHtml.append("<tr><td>" + entrySet.getKey() + "</td>");
                                //System.out.println(l[2]);
                                //                               System.out.println("================进入了getMetric");
                                String metricPath = MetricUtil.getMetric(l, propers, pr);
                                for (String s : l) stringHtml.append("<td>" + s + "</td>\n");
                                if (metricPath == null || metricPath.length() <= 0) {
                                    stringHtml.append("<td>" + "metric未获得，可联系Frank.Niu查看原因" + "</td>\n");
                                } else if (metricPath.contains("error")) {
                                    stringHtml.append("<td>" + metricPath + "</td>\n");
                                } else {
//                                stringHtml.append("<td>" + metrics.get(0) + "</td>\n");
                                    stringHtml.append("<td>" + "<a href=\"http://192.168.101.29:8082/" + metricPath + "\">下载metric</a></td>\n");
                                }
                                stringHtml.append("</tr>\n");
                            }
                        });
                    }
                }
            }
            stringHtml.append("</body></html>");

            //将HTML文件内容写入文件中
            printStream.println(stringHtml.toString());

            //新增用例数和错误用例数写入本地文件
            file = new File(curpath + "inject_variables.properties");
            if (!file.exists()) file.createNewFile();
            System.out.println("newCaseCount=" + latestSet.size());
            System.out.println("\nerrCaseCount=" + errSet.size());
            System.out.println("\nfallCaseCount=" + fallSet.size());
            System.out.println("\nupCaseCount=" + upSet.size());
            System.out.println("\nnormalCount=" + normalSet.size());
            System.out.println("\navgScore=" + score.get(0));
            System.out.println("\navgConScore=" + score.get(1));
            StringBuilder fallCases = new StringBuilder();
            List<String> newFallcaseList = fallcaseList.stream().distinct().collect(Collectors.toList());
            for (int i = 0; i < newFallcaseList.size(); i++) {
                fallCases.append(newFallcaseList.get(i));
                if (i < fallSet.size() - 1) {
                    fallCases.append(",");
                }
            }
            PrintStream printFileStream = new PrintStream(new FileOutputStream(file));
            printFileStream.println("newCaseCount=" + latestSet.size() + "\nerrCaseCount=" + errSet.size() +
                    "\nfallCaseCount=" + fallSet.size() + "\nupCaseCount=" + upSet.size() + "\nnormalCount=" + normalSet.size() +
                    "\navgScore=" + score.get(0) + "\navgConScore=" + score.get(1) + "\nnumber=" + number + "\nfallCaseList=" + fallCases);
        } catch (IOException e) {
            e.printStackTrace();
        } catch (Exception e) {
            e.printStackTrace();
        }
        return isMerge;
    }

    private static void PostProcessLatestMergedPrid(List<Deque> pathList, PR pr) throws Exception {
        Deque<PR> releaseDeque = null;
        Deque<PR> featureDeque = null;
        Deque<PR> featurePolarsllvmPrIdDeque = null;

        String branch = pr.getDisplayId();
        if (branch.equals("feature")) featureDeque = pathList.get(0);
        if (branch.equals("release")) releaseDeque = pathList.get(1);
        if (branch.equals("feature/polars-llvm")) featurePolarsllvmPrIdDeque = pathList.get(2);
        int count = 0;
        while (featureDeque != null && !featureDeque.isEmpty()) {
            PR mergedPr = featureDeque.removeFirst();
            mergedPrId = mergedPr.getPrId();

            //读取jsyUnitTest中的单元测试时间，如果closedDate 大于 executetime 就舍弃
            System.out.println("select executeTime from jsyUnitTest where prId=\"" + pr.getPrId() + "\";");
            Long executeTime = getBiggestTimeStamp(JSYDBUtils.query("select executeTime from jsyUnitTest where prId=\"" + pr.getPrId() + "\";", "executeTime"));
            executeTime = executeTime == 0L ? Long.MAX_VALUE : executeTime;
            System.out.println("===========================executeTime = " + executeTime);

            String filePath = null;
            if (pr.getTask().getCodeTypes()[0].equals("java")) {
                filePath = curpath + mergedPrId + "-" + pr.getTask().getDataTypes()[0] + ".csv";
            } else if (pr.getTask().getCodeTypes()[0].equals("c++")) {
                filePath = curpath + mergedPrId + "-" + pr.getTask().getDataTypes()[0] + "_cpp.csv";
            }
            File featureFile = new File(filePath);
            System.out.println("mergedPr.getClosedDate():" + mergedPr.getClosedDate() + ",executeTime:" + executeTime);
            System.out.println((mergedPr.getClosedDate() > executeTime) || !featureFile.exists() || featureFile.length() == 0);

            System.out.println((mergedPr.getClosedDate() > executeTime));
            System.out.println("featureFile.exists()+ " + (!featureFile.exists()) + "featureFileNme = " + featureFile.getName());
            System.out.println("featureFile.length() == 0" + (featureFile.length() == 0));
            if (count == 3) {
                break;
            } else if ((mergedPr.getClosedDate() > executeTime) || !featureFile.exists() || featureFile.length() == 0) {
                continue;
            } else if (count++ < 3) {

                //检测csv文件是否正确
                if (CsvFileCorrectness(featureFile)) {
                    BaseLinePaths.add(filePath);
                    mergedPirds.add(mergedPrId);
                } else {
                    count--;
                }

            }
        }

        while (releaseDeque != null && !releaseDeque.isEmpty()) {
            PR mergedPr = releaseDeque.removeFirst();
            mergedPrId = mergedPr.getPrId();

            //读取jsyUnitTest中的单元测试时间，如果closedDate 大于 executetime 就舍弃
            System.out.println("select executeTime from jsyUnitTest where prId=\"" + pr.getPrId() + "\";");
            Long executeTime = getBiggestTimeStamp(JSYDBUtils.query("select executeTime from jsyUnitTest where prId=\"" + pr.getPrId() + "\";", "executeTime"));
            executeTime = executeTime == 0L ? Long.MAX_VALUE : executeTime;

            String filePath = null;
            if (pr.getTask().getCodeTypes()[0].equals("java")) {
                filePath = curpath + mergedPrId + "-" + pr.getTask().getDataTypes()[0] + ".csv";
            } else if (pr.getTask().getCodeTypes()[0].equals("c++")) {
                filePath = curpath + mergedPrId + "-" + pr.getTask().getDataTypes()[0] + "_cpp.csv";
            }
            File releaseFile = new File(filePath);

            System.out.println("mergedPr.getClosedDate():" + mergedPr.getClosedDate() + ",executeTime:" + executeTime);
            System.out.println((mergedPr.getClosedDate() > executeTime) || !releaseFile.exists() || releaseFile.length() == 0);

            if (count == 3) {
                break;
            } else if ((mergedPr.getClosedDate() > executeTime) || !releaseFile.exists() || releaseFile.length() == 0) {
                continue;
            } else if (count++ < 3) {

                //检测csv文件是否正确
                if (CsvFileCorrectness(releaseFile)) {
                    BaseLinePaths.add(filePath);
                    mergedPirds.add(mergedPrId);
                } else {
                    count--;
                }
            }
        }

        while (featurePolarsllvmPrIdDeque != null && !featurePolarsllvmPrIdDeque.isEmpty()) {
            PR mergedPr = featurePolarsllvmPrIdDeque.removeFirst();
            mergedPrId = mergedPr.getPrId();

            //读取jsyUnitTest中的单元测试时间，如果closedDate 大于 executetime 就舍弃
            //System.out.println("select executeTime from jsyUnitTest where prId=\"" + pr.getPrId() + "\";");
            //Long executeTime = getBiggestTimeStamp(JSYDBUtil.query("select executeTime from jsyUnitTest where prId=\"" + pr.getPrId() + "\";", "executeTime"));
            //llvm分支目前没有单测，代码打包的时间就是benchmark的执行时间
            Long executeTime = System.currentTimeMillis();
            executeTime = executeTime == 0L ? Long.MAX_VALUE : executeTime;
            System.out.println("===========================executeTime = " + executeTime);

            String filePath = null;
            if (pr.getTask().getCodeTypes()[0].equals("java")) {
                filePath = curpath + mergedPrId + "-" + pr.getTask().getDataTypes()[0] + ".csv";
            } else if (pr.getTask().getCodeTypes()[0].equals("c++")) {
                filePath = curpath + mergedPrId + "-" + pr.getTask().getDataTypes()[0] + "_cpp.csv";
            }
            File featureFile = new File(filePath);

            System.out.println("mergedPr.getClosedDate():" + mergedPr.getClosedDate() + ",executeTime:" + executeTime);
            System.out.println((mergedPr.getClosedDate() > executeTime) || !featureFile.exists() || featureFile.length() == 0);

            System.out.println((mergedPr.getClosedDate() > executeTime));
            System.out.println("featureFile.exists()+ " + (!featureFile.exists()) + "featureFileNme = " + featureFile.getName());
            System.out.println("featureFile.length() == 0" + (featureFile.length() == 0));
            if (count == 3) {
                break;
            } else if ((mergedPr.getClosedDate() > executeTime) || !featureFile.exists() || featureFile.length() == 0) {
                continue;
            } else if (count++ < 3) {

                //检测csv文件是否正确
                if (CsvFileCorrectness(featureFile)) {
                    BaseLinePaths.add(filePath);
                    mergedPirds.add(mergedPrId);
                } else {
                    count--;
                }
            }
        }
    }


    public static long getBiggestTimeStamp(List<Map<String, String>> list) {
        long result = 0L;
        if (list == null || list.isEmpty()) {
            return result;
        }
        for (Map<String, String> map : list) {
            if (map.containsKey("executeTime")) {
                long aLong = Long.parseLong(map.get("executeTime"));
                result = Math.max(result, aLong);
            }
        }
        return result;
    }

    public static List<Deque> getLatestMergedPrid() {
        List<Deque> res = new ArrayList<>();
        int start = 0;
        Deque<PR> featurePrIdDeque = new LinkedList<>();
        Deque<PR> releasePrIdDeque = new LinkedList<>();
        Deque<PR> featurePolarsllvmPrIdDeque = new LinkedList<>();
        try {
            while (featurePrIdDeque.size() <= 25 || releasePrIdDeque.size() <= 25) {
                System.out.println("开始获取cookie");
                String cookie = getCookie();

                String url = "https://code.fineres.com/projects/CAL/repos/polars/pull-requests?state=MERGED" + "&start=" + start + "&reviewer=";
                start += 25;
                URLConnection urlConnection = new URL(url).openConnection();
                urlConnection.setRequestProperty("Cookie", cookie);
                HttpURLConnection connection = (HttpURLConnection) urlConnection;
                connection.setRequestMethod("GET");
                connection.setConnectTimeout(5000);
                connection.connect();

                StringBuffer response = new StringBuffer();

                BufferedReader in = new BufferedReader(
                        new InputStreamReader(urlConnection.getInputStream()));
                String inputLine;

                while ((inputLine = in.readLine()) != null) {
                    response.append(inputLine);
                }

                JSONArray jsonArray = JSON.parseArray(response.toString().split("\"values\":")[1].split(",\"start\":")[0]);

                for (int i = 0; i < jsonArray.size(); i++) {
                    JSONObject jsonObject = jsonArray.getJSONObject(i);
                    String prId = jsonObject.getString("id");
                    String displayId = jsonObject.getJSONObject("toRef").getString("displayId");

                    PR pr = new PR(displayId, jsonObject.getJSONObject("author").getJSONObject("user").getString("displayName"), prId);
                    pr.setClosedDate(jsonObject.getLong("closedDate"));

                    if (displayId.equals("feature/3.0")) {
                        //System.out.println("feature:" + prId);
                        featurePrIdDeque.add(pr);
                    } else if (displayId.equals("release/3.0")) {
                        //System.out.println("release:" + prId);
                        releasePrIdDeque.add(pr);
                    } else if (displayId.equals("feature/polars-llvm")) {
                        //System.out.println("feature/polars-llvm:" + prId);
                        featurePolarsllvmPrIdDeque.add(pr);
                    }
                }
            }
            res.add(featurePrIdDeque);
            res.add(releasePrIdDeque);
            res.add(featurePolarsllvmPrIdDeque);
        } catch (IOException e) {
            e.printStackTrace();
        }

        return res;
    }

    public static boolean CsvFileCorrectness(File file) {
        //检测csv文件是否正确,最后一行是否包含29个逗号
        boolean contains29Commas = false;

        try (BufferedReader br = new BufferedReader(new FileReader(file))) {
            String line;
            String lastLine = null;

            // Read lines from the file until reaching the end
            while ((line = br.readLine()) != null) {
                lastLine = line;
            }

            // Check if the last line is not null
            if (lastLine != null) {
                // Count the number of commas in the last line
                int commaCount = countOccurrences(lastLine, ',');
                contains29Commas = commaCount >= 29;
            }

        } catch (IOException e) {
            e.printStackTrace();
        }
        return contains29Commas;
    }

    private static int countOccurrences(String text, char character) {
        int count = 0;
        for (int i = 0; i < text.length(); i++) {
            if (text.charAt(i) == character) {
                count++;
            }
        }
        return count;
    }


    public static String getCookie() {
        String url = "https://code.fineres.com/j_atl_security_check";
        URLConnection urlConnection;
        String rememberme = null;
        try {
            String param = "j_username=Sun.Sun&j_password=sunmuchao980320$$&_atl_remember_me=on&submit=登录&scan=企业微信扫码登录";
            urlConnection = new URL(url).openConnection();
            HttpURLConnection conn = (HttpURLConnection) urlConnection;
            conn.setInstanceFollowRedirects(false);
            conn.setDoOutput(true);
            conn.setDoInput(true);
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(5000);
            conn.setRequestProperty("Cookie", "_ga=GA1.2.145599097.1623144057; SPC-SELECTED-CATEGORY-CORE=all; SPC-SELECTED-CATEGORY=18; BITBUCKETSESSIONID=34C6CC0F403F81E0228EC169B4904E4D");
            OutputStream os = conn.getOutputStream();
            if (param != null && param.length() > 0) os.write(param.getBytes());
            rememberme = conn.getHeaderField("Set-Cookie").split(";")[0];
        } catch (Exception e) {
            e.printStackTrace();
        }
        return rememberme;
    }

    static class Case {
        private int systemCpuCountInt = 0;
        private String UUID;
        private String runnerIp = "";
        private String categoryName = "";
        private String caseName = "";
        private long avgConTime = 0;
        private String fieldInfo = "";
        private long avgWarmTime = 0;
        private long avgMeasureTime = 0;
        private int realConMeasureSize = 0;
        private int conFailedCount = 0;
        private long avgMeasureGcTime = 0;
        private long measureJvmMemUsedMaxUsage = 0;
        private long polarsMemUsedMaxUsage = 0;
        private String errorInfo = "";

        public Case() {
        }

        public void setUUID(String runnerIp, String categoryName, String caseName) {
            this.UUID = runnerIp  + "_" + categoryName + "_" + caseName;
            this.runnerIp = runnerIp;
            this.categoryName = categoryName;
            this.caseName = caseName;
        }

        public String getRunnerIp() {
            return runnerIp;
        }

        public String getCategoryName() {
            return categoryName;
        }

        public String getCaseName() {
            return caseName;
        }

        public String getUUID() {
            return UUID;
        }

        public void setCpuCount(String systemCpuCount) {
            this.systemCpuCountInt = Integer.valueOf(systemCpuCount);
        }

        public int getCpuCount() {
            return systemCpuCountInt;
        }

        public void setFieldInfo(String fieldInfo) {
            this.fieldInfo = fieldInfo;
        }

        public String getFieldInfo() {
            return fieldInfo;
        }

        public void setAvgWarmTime(long avgWarmTime) {
            this.avgWarmTime = avgWarmTime;
        }

        public double getAvgWarmTime() {
            return avgWarmTime;
        }

        public void setAvgMeasureTime(long avgMeasureTime) {
            this.avgMeasureTime = avgMeasureTime;
        }

        public float getAvgMeasureTime() {
            return avgMeasureTime;
        }

        public void setAvgConTime(long avgConTime) {
            this.avgConTime = avgConTime;
        }

        public double getAvgConTime() {
            return avgConTime;
        }

        public void setRealConMeasureSize(Integer realConMeasureSize) {
            this.realConMeasureSize = realConMeasureSize;
        }

        public int getRealConMeasureSize() {
            return realConMeasureSize;
        }

        public void setConFailedCount(Integer conFailedCount) {
            this.conFailedCount = conFailedCount;
        }

        public int getConFailedCount() {
            return conFailedCount;
        }

        public void setAvgMeasureGcTime(long avgMeasureGcTime) {
            this.avgMeasureGcTime = avgMeasureGcTime;
        }

        public float getAvgMeasureGcTime() {
            return avgMeasureGcTime;
        }

        public void setMeasureJvmMemUsedMaxUsage(long measureJvmMemUsedMaxUsage) {
            this.measureJvmMemUsedMaxUsage = measureJvmMemUsedMaxUsage;
        }

        public Long getMeasureJvmMemUsedMaxUsage() {
            return measureJvmMemUsedMaxUsage;
        }

        public void setPolarsMemUsedMaxUsage(long polarsMemUsedMaxUsage) {
            this.polarsMemUsedMaxUsage = polarsMemUsedMaxUsage;
        }

        public Long getPolarsMemUsedMaxUsage() {
            return polarsMemUsedMaxUsage;
        }

        public void setErrorInfo(String errorInfo) {
            this.errorInfo = errorInfo;
        }

        public String getErrorInfo() {
            return errorInfo;
        }

    }

    public static void main(String[] args) {
        long startTime = System.currentTimeMillis();
        String prid = args[0];
        String branch = args[1];
        String dataType = args[2];
        String codeType = args[3];
        PR pr = new PR(branch, "", prid);
        pr.buildTask("benchmark", new String[]{dataType}, new String[]{codeType});
        try {
            showResult(pr);
            long stopTime = System.currentTimeMillis();
            System.out.println("BanchMarckParser执行了" + ((stopTime - startTime) / 1000) + "秒");
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}