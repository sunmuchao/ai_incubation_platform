package metric;

import metric.lineInfo.AggregateLineInfo;
import metric.lineInfo.FilterLineInfo;
import metric.lineInfo.JoinLineInfo;
import metric.lineInfo.LineInfo;
import metric.lineInfo.NormalLineInfo;
import metric.lineInfo.UnionLineInfo;

import java.util.ArrayList;

public class MetricPostProcessor {
    public LineInfo process(MetricNode curNode){
        if (curNode.getData().getOperate().contains("Join")) {
            //如果当前行为join
            //curNode.getData().setFields(curNode.getInfo().split("\\[")[3].split("]")[0].split(","));
            MetricNode left = curNode.leftNode;
            //processDataNode(left);
            MetricNode right = curNode.getRightNodes().get(0);
            //processDataNode(right);
            JoinLineInfo joinLineInfo = new JoinLineInfo(curNode.getData(), left.getData(), right.getData());
            return joinLineInfo;
        } else if (curNode.getData().getOperate().contains("Union")) {
            //如果当前行为union
            //processDataNode(curNode);
            ArrayList<LineInfo> sonTableInfos = new ArrayList<>();
            for (MetricNode node : curNode.getRightNodes()) {
                //node = processLimitNode(node);
                sonTableInfos.add(node.getData());
            }
            //MetricNode left = processLimitNode(curNode.leftNode);
            MetricNode left = curNode.leftNode;
            sonTableInfos.add(left.getData());
            UnionLineInfo unionLineInfo = new UnionLineInfo(curNode.getData());
            unionLineInfo.addSonTableInfos(sonTableInfos);
            return unionLineInfo;
        } else if (curNode.getData().getOperate().contains("Aggregate")) {
            //如果当前行为分组汇总
            curNode.getData().setAggFields(curNode.getInfo().split("group=\\[")[1].split("]")[0].split(","));
            curNode.getData().setGroupFields(curNode.getInfo().split("agg=\\[")[1].split("]")[0].split(","));
            //processDataNode(curNode.leftNode);
            AggregateLineInfo aggregateLineInfo = new AggregateLineInfo(curNode.getData(), curNode.leftNode.getData());
            return aggregateLineInfo;
        } else if(curNode.getData().getOperate().contains("Filter") || curNode.getData().getOperate().contains("Project")){
            System.out.println(curNode.getInfo());
            if(!curNode.getInfo().split("\\[")[1].equals("]")){
                //如果当前行为过滤操作
                curNode.getData().setFormula(curNode.getInfo().split("\\[")[1].split("]")[0]);
            }
            MetricNode left = curNode.leftNode;
            //processDataNode(left);
            FilterLineInfo filterLineInfo = new FilterLineInfo(curNode.getData(), left.getData());
            return filterLineInfo;
        }else{
            NormalLineInfo normalLineInfo = null;
            //processDataNode(curNode);
            if(curNode.leftNode != null) {
                MetricNode left = curNode.leftNode;
                //processDataNode(left);
                normalLineInfo = new NormalLineInfo(curNode.getData(), left.getData());
            }
            normalLineInfo = new NormalLineInfo(curNode.getData());
            return normalLineInfo;
        }
    }

    public MetricNode processLimitNode(MetricNode node){
        if (node.getData().getOperate().contains("Limit")) {
            //如果当前行为limit,需向下访问一层判断字段数
            //node.getData().setFields(node.getLeftNode().getInfo().split("outputs=\\[")[1].split("]")[0].split(","));
        } else {
            //processDataNode(node);
        }
        return node;
    }

    public void processDataNode(MetricNode node){
        if(node.getInfo().contains("outputs=")){
            String[] fields = node.getInfo().split("outputs=\\[")[1].split("]");
            if(fields.length > 0) {
                node.getData().setFields(fields[0].split(","));
            }
        } else {
            node.getData().setFields(node.getInfo().split("\\[")[1].split("]")[0].split(","));
        }

    }
}
