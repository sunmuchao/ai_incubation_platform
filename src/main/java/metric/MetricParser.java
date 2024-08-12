package metric;

import ci.benchMark.SuiteUtil;
import metric.classify.Classifier;
import metric.lineInfo.LineInfo;

import java.io.BufferedReader;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileReader;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Stack;

import base.config.Application;

public class MetricParser {
    private String metricPath;

    public MetricParser(String metricPath) {
        this.metricPath = metricPath;
    }

    //解析matric
    public void parse() throws Exception {
        File metricFile = new File(metricPath);
        //获取metric执行时间
        BufferedReader reader = new BufferedReader(new FileReader(metricPath));
        String metricDate = reader.readLine().split(",")[0];
        String lastLine = readLastLine(metricFile);
        ArrayList<String> metric = null;
        if (lastLine.contains("OutputOperator"))
            metric = metricPostProcess(getMetric(metricPath));
        else if (lastLine.contains("dataSource"))
            metric = metricPostProcess(getUpdateMetric(metricPath));

        if (metric != null) {
            ArrayList<String> optimizedInfo = getOptimizedInfo(metricPath);
            MetricNode root = createMetricTree(new MetricNode(parseLine(metric.get(0))), metric);
            //查找node对应的optimizedInfo
            //获取node的point，代表为tree的第几层，查看是父节点的左节点还是右节点，如果是左节点的话不向上找，否则的话，向上再遍历一层
            MetricNode node = setNodeInfo(getMaxTimeNode(root), optimizedInfo, 0);
            node.setDate(metricDate);
            Classifier classifier = new Classifier();
            String dirName = classifier.classify(node, metricFile);
            if (dirName != null && !dirName.equals("不需要被记录")) {
                //如果目录不存在，则导入benchmark
                SuiteUtil suiteUtil = new SuiteUtil();
                suiteUtil.importSuiteToBenchmark(Application.suitePath, dirName, "/data/ContinuousIntegration/polars_test-benchmark/suite");
            }
            MetricNode curNode = root;
            //遍历每一个节点,并将结果入库
            while (curNode.leftNode != null) {
                curNode = curNode.leftNode;
                curNode = setNodeInfo(curNode, optimizedInfo, 0);
                curNode.setDate(metricDate);
                classifier = new Classifier();
                classifier.classify(curNode, metricFile);
            }
        }
    }

    private ArrayList<String> metricPostProcess(ArrayList<String> metric) {
        //如果当前的是Pre，则pre++,
        //如果是join或者union，则存入stack
        // 如果是上一行比该行点数少，则从堆栈中去点数
        Stack<OperateMap> joinStack = new Stack<>();
        ArrayList<String> newMetric = new ArrayList<>();
        //如果是更新的metric,所有的ponit-1
        int updatePoint = 0;
        if (metric.get(metric.size() - 1).contains("ChecksumImportDataBracket")) {
            updatePoint = 1;
        }

        int pre = 0;
        int curPre = 0;
        int prePointNumber = 0;
        for (int i = metric.size() - 1; i >= 0; i--) {
            if (metric.get(i).contains("Pre(")) {
                if (joinStack.size() != 0 && joinStack.peek().getOperate().equals("Union")) {
                    int curPointNumber = splitPonit(metric.get(i).split(" ")[1]) - updatePoint;
                    if (curPointNumber < prePointNumber) {
                        curPre = 0;
                    }
                    curPre++;
                } else
                    pre++;
                continue;
            }
            //记录上一次的·的数量
            String s = null;
            String[] splits = metric.get(i).split(" ");

            int curPointNumber = splitPonit(splits[1]);
            if (curPointNumber < prePointNumber) {
                curPre = 0;
                if (joinStack.peek().getOperate().equals("Join")) {
                    pre = joinStack.pop().getPre();
                } else if (joinStack.size() != 0 && curPointNumber == joinStack.peek().getPoint() - joinStack.peek().getPre() + curPre + 1) {
                    pre = joinStack.peek().getPre();
                } else if (joinStack.size() != 0 && curPointNumber < joinStack.peek().getPoint() - joinStack.peek().getPre() + curPre + 1) {
                    joinStack.pop();
                }

            } else if (joinStack.size() != 0 && curPointNumber == joinStack.peek().getPoint() - joinStack.peek().getPre() + curPre + 1) {
                pre = joinStack.peek().getPre();
            }

            splits[1] = splits[1].substring(pre + curPre + updatePoint);
            s = String.join(" ", splits);
            if (metric.get(i).contains("Join")) {
                joinStack.push(new OperateMap("Join", pre));
            } else if (metric.get(i).contains("Union")) {
                OperateMap operateMap = new OperateMap("Union", pre);
                operateMap.setPoint(curPointNumber);
                joinStack.push(operateMap);
            }
            prePointNumber = curPointNumber;
            newMetric.add(s);
        }
        return newMetric;
    }

    private MetricNode setNodeInfo(MetricNode node, ArrayList<String> optimizedInfo, int deep) {
        int count = 0;
        MetricNode root = node;
        ArrayList<MetricNode> rightNodes = null;
        MetricNode preNode = null;

        //for (int i = optimizedInfo.size() - 2; i >= 0; i--) {
        for (int i = 0; i < optimizedInfo.size(); i++) {
            //提前中断
            if(node.getInfo() != null){
                return root;
            }
            if (node.getData().getPoint() == splitPonit(optimizedInfo.get(i).split(" ")[0].substring(1))) {
                //System.out.println(optimizedInfo.get(i));
                node.setInfo(optimizedInfo.get(i));
                //如果当前节点为"limit,window",通过递归+回溯 将其左子节点信息赋予该节点。只递归一次
                if(deep == 1) return root;
                node = setSonNodeInfo(node, optimizedInfo, deep);
                //如果当前节点的operate为"Join/Union"，则需要赋值左右节点信息
                if ((node.getData().getOperate().contains("Join") || node.getData().getOperate().contains("Union")) && count == 0) {
                    preNode = node;
                    rightNodes = node.getRightNodes();
                    node = rightNodes.get(count++);
                } else if (count != 0 && count < rightNodes.size()) {
                    node = rightNodes.get(count++);
                } else if (rightNodes != null && count == rightNodes.size()) {
                    node = preNode.leftNode;
                }
            }
        }
        return root;
    }

    private MetricNode setSonNodeInfo(MetricNode node, ArrayList<String> optimizedInfo, int deep) {
        if (!node.getData().getOperate().contains("Join") && !node.getData().getOperate().contains("Union") && node.leftNode != null && deep == 0) {
            MetricNode curNode = node;
            deep = 1;
            setNodeInfo(node.leftNode, optimizedInfo, deep);
            node = curNode;
        }
        return node;
    }

    private MetricNode getMaxTimeNode(MetricNode root) {
        MetricNode curNode = root;
        MetricNode maxNode = null;
        int maxTime = 0;
        while (curNode != null) {
            int preOpenTime = curNode.getData().getOpenTime();
            int preComputeTime = curNode.getData().getComputeTime();
            MetricNode preNode = curNode;
            if (curNode.leftNode != null) {
                curNode = curNode.leftNode;
                int curTime = curNode.getData().getTime();
                curNode.setParentRelationShip("left");

                int preNodeOpenTime = (preOpenTime - curNode.getData().getOpenTime()) >= 0 ? preOpenTime - curNode.getData().getOpenTime() : preOpenTime;
                int preNodeComputeTime = (preComputeTime - curNode.getData().getComputeTime()) >= 0 ? preComputeTime - curNode.getData().getComputeTime() : preComputeTime;
                preNode.getData().setOpenTime(preNodeOpenTime);
                preNode.getData().setComputeTime(preNodeComputeTime);
                if (preOpenTime + preComputeTime - curTime > maxTime) {
                    maxTime = preOpenTime + preComputeTime - curNode.getData().getTime();
                    maxNode = preNode;
                }
            } else {
                //代表第一行
                if (preOpenTime + preComputeTime - 0 > maxTime) {
                    maxTime = preOpenTime + preComputeTime - 0;
                    preNode.getData().setOpenTime(preOpenTime - 0);
                    preNode.getData().setComputeTime(preComputeTime - 0);
                    maxNode = preNode;
                }
                curNode = null;
            }
        }
        return maxNode;
    }

    private MetricNode createMetricTree(MetricNode root, ArrayList<String> metric) {
        MetricNode curNode = root;
        //用来记录join、union节点的堆栈
        Stack<MetricNode> joinStack = new Stack<>();

        for (int i = 1; i < metric.size(); i++) {
            LineInfo lineInfo = parseLine(metric.get(i));
            MetricNode node = new MetricNode(lineInfo);
            if (node.getData().getOperate().contains("Join") || node.getData().getOperate().contains("Union")) {
                joinStack.add(node);
            }

            //默认为左子树
            if (curNode.getData().getPoint() + 1 == lineInfo.getPoint()) {
                if (curNode.leftNode == null && !curNode.getData().getOperate().contains("Join") && !curNode.getData().getOperate().contains("Union")) {
                    curNode.leftNode = node;
                    curNode = curNode.leftNode;
                } else {
                    curNode.addRightNode(node);
                    ArrayList<MetricNode> rightNodes = curNode.getRightNodes();
                    curNode = rightNodes.get(rightNodes.size() - 1);
                }
            } else if (curNode.getData().getPoint() >= lineInfo.getPoint()) {
                lineInfo.setPoint(lineInfo.getPoint());
                if (!joinStack.isEmpty()) {
                    if (joinStack.peek().getData().getOperate().equals("UnionOperator")) {
                        if (joinStack.peek().getData().getPoint() == lineInfo.getPoint() - 1) {
                            curNode = joinStack.peek();
                            curNode.addRightNode(node);
                            ArrayList<MetricNode> rightNodes = curNode.getRightNodes();
                            curNode = rightNodes.get(rightNodes.size() - 1);
                        } else {
                            //将右子树最后一个节点变为左子树
                            MetricNode tmpNode = joinStack.pop();
                            ArrayList<MetricNode> rightNodes = tmpNode.getRightNodes();
                            tmpNode.leftNode = rightNodes.remove(rightNodes.size() - 1);
                            curNode = joinStack.pop();
                        }
                    } else if (joinStack.peek().getData().getOperate().contains("Join")) {
                        curNode = joinStack.pop();
                        curNode.leftNode = node;
                        curNode = curNode.leftNode;
                    }
                }
            }
        }
        //尾处理
        while (!joinStack.isEmpty()) {
            MetricNode tmpNode = joinStack.pop();
            ArrayList<MetricNode> rightNodes = tmpNode.getRightNodes();
            tmpNode.leftNode = rightNodes.remove(rightNodes.size() - 1);
        }
        return root;
    }

    public static String readLastLine(File file) {
        String lastLine = "";
        try (BufferedReader bufferedReader = new BufferedReader(new FileReader(file))) {
            String currentLine;
            while (!(currentLine = bufferedReader.readLine()).equals("") || !(bufferedReader.readLine()).equals("")) {
                lastLine = currentLine;
            }
        } catch (Exception e) {
            e.getMessage();
        }
        System.out.println("lastLine=" + lastLine);
        return lastLine;
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

    public static int splitPonit(String str) {
        char[] cs = str.toCharArray();
        for (int i = 0; i < cs.length; i++) {
            if (cs[i] != '·' && cs[i] != '?') {
                return i;
            }
        }
        return 0;
    }

    public static ArrayList<String> getMetric(String metricPath) throws IOException, InterruptedException {
        BufferedReader reader = new BufferedReader(new FileReader(metricPath));
        boolean isMetric = false;
        String line;
        ArrayList<String> metric = new ArrayList<>();
        boolean isOutputOperator = false;
        while (!isOutputOperator) {
            line = reader.readLine();
            //当前行为内存统计，获取峰值内存大于某一阀值的数据加入到宕机环境
            //阀值先设置为1G
            if (line.contains("peakUserMemory")) {
                String peakUserMemory = line.split("peakUserMemory=")[1].split(",")[0];
                if (Long.parseLong(peakUserMemory) >= 1073741824) {
                    String[] metricPaths = metricPath.split("/");
                    String taskName = metricPaths[metricPaths.length - 1].split("\\.")[0];
                    SuiteUtil suiteUtil = new SuiteUtil();
                    suiteUtil.importSuiteToBenchmark(Application.suitePath,
                            taskName, "/data/smc/polars_delay_data");
                }
            }

            if (line.equals("metric:")) {
                isMetric = true;
                continue;
            }
            if (!isMetric) continue;

            //获取耗时最长的operate，先存入内存，然后逆序输出
            metric.add(line);
            if (line.contains("OutputOperator")) {
                isOutputOperator = true;
            }
        }

        return metric;
    }

    private ArrayList<String> getUpdateMetric(String metricPath) throws IOException {
        BufferedReader reader = new BufferedReader(new FileReader(metricPath));
        boolean isMetric = false;
        String line;
        ArrayList<String> metric = new ArrayList<>();
        boolean isChecksumImportDataBracket = false;
        while (!isChecksumImportDataBracket) {
            line = reader.readLine();
            System.out.println("line:" + line);
            if (line.equals("metric:")) {
                isMetric = true;
                continue;
            }
            if (!isMetric) continue;

            //获取耗时最长的operate，先存入内存，然后逆序输出
            metric.add(line);
            if (line.contains("ChecksumImportDataBracket")) {
                isChecksumImportDataBracket = true;
            }
        }
        return metric;
    }

    public static ArrayList<String> getOptimizedInfo(String metricPath) throws IOException {
        BufferedReader reader = new BufferedReader(new FileReader(metricPath));
        boolean isOptimizedInfo = false;
        String line;
        boolean isOutputNode = false;
        ArrayList<String> optimizedInfo = new ArrayList<>();
        while (!isOutputNode) {
            line = reader.readLine();
            if (line.equals("optimized info:")) {
                isOptimizedInfo = true;
                continue;
            }
            if (!isOptimizedInfo) continue;
            //获取耗时最长的operate，先存入内存，然后逆序输出
            optimizedInfo.add(line);
            if (line.contains("OutputNode")) isOutputNode = true;
        }
        return optimizedInfo;
    }

    public static LineInfo parseLine(String line) {
        String[] s = line.split("sum=");
        String operate = line.split(" ")[1];
        LineInfo lineInfo = new LineInfo.Builder()
                .setOperate(operate.substring(splitPonit(operate)))
                .setRows(Integer.parseInt(line.split("rows=")[1].split(" ")[0]))
                .setCols(Integer.parseInt(line.split("cols=")[1].split(" ")[0]))
                .setComputeTime(Integer.parseInt(s[2].split("ms")[0]))
                .setTime(Integer.parseInt(s[1].split("ms")[0]))
                .setPonit(splitPonit(operate))
                .setLineNumber(line.split(" ")[0])
                .build();
        return lineInfo;
    }
}
