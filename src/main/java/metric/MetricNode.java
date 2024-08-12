package metric;

import metric.lineInfo.LineInfo;

import java.util.ArrayList;

public class MetricNode {
    private LineInfo data;

    public MetricNode leftNode;

    private ArrayList<MetricNode> rightNodes;

    private String parentRelationShip;

    private int level;

    private String info;

    //metric执行时间
    private String date;

    public MetricNode(LineInfo data) {
        this.data = data;
    }


    public String getDate() {
        return date;
    }

    public void setDate(String date) {
        this.date = date;
    }

    public LineInfo getData() {
        return data;
    }

    public MetricNode getLeftNode() {
        return leftNode;
    }


    public void setData(LineInfo data) {
        this.data = data;
    }

    public void setLeftNode(MetricNode leftNode) {
        this.leftNode = leftNode;
    }

    public String getParentRelationShip() {
        return parentRelationShip;
    }

    public void setParentRelationShip(String parentRelationShip) {
        this.parentRelationShip = parentRelationShip;
    }

    public int getLevel() {
        return level;
    }

    public void setLevel(int level) {
        this.level = level;
    }

    public String getInfo() {
        return info;
    }

    public void setInfo(String info) {
        this.info = info;
    }

    public ArrayList<MetricNode> getRightNodes() {
        if(rightNodes != null) return rightNodes;
        return null;
    }

    public void addRightNode(MetricNode rightNode) {
        if(rightNodes == null) rightNodes = new ArrayList<>();
        rightNodes.add(rightNode);
    }
}