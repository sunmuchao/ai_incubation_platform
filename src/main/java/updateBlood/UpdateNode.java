package updateBlood;

import com.google.common.graph.MutableGraph;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

public class UpdateNode {
    private String dagId;
    private String tableId;
    private String tableName;
    private int actualWrite;
    private MutableGraph<String> graph;
    //父表数量
    private int parenttableNumber;
    //更新的父表数量
    private int updatedParenttableNumber;
    //父表中ActualWrite=0 的数量, -1代表当前节点actualWrite!=0 或者 没有父节点
    private int parenttableActualWriteIsZeroNumber;
    //记录经过的前驱节点
    public Set<String> predecessorNodeSet;
    //记录的是当前节点的每条血缘路径上的节点数
    public Map<String, Integer> successorNodes;


    UpdateNode(Builder builder){
        this.dagId = builder.dagId;
        this.tableId = builder.tableId;
        this.tableName = builder.tableName;
        this.actualWrite = builder.actualWrite;
        parenttableNumber = 0;
        updatedParenttableNumber = 0;
        parenttableActualWriteIsZeroNumber = 0;
        predecessorNodeSet = new HashSet<>();
        successorNodes = new HashMap<>();
    }

    public UpdateNode(){
    }

    public Map<String, Integer> getSuccessorNodes() {
        return successorNodes;
    }

    public int getUpdatedParenttableNumber() {
        return updatedParenttableNumber;
    }

    public void setUpdatedParenttableNumber(int updatedParenttableNumber) {
        this.updatedParenttableNumber = updatedParenttableNumber;
    }

    public Set<String> getPredecessorNodeSet() {
        return predecessorNodeSet;
    }

    public int getParenttableNumber() {
        return parenttableNumber;
    }

    public void setParenttableNumber(int parenttableNumber) {
        this.parenttableNumber = parenttableNumber;
    }

    public int getParenttableActualWriteIsZeroNumber() {
        return parenttableActualWriteIsZeroNumber;
    }

    public void setParenttableActualWriteIsZeroNumber(int parenttableActualWriteIsZeroNumber) {
        this.parenttableActualWriteIsZeroNumber = parenttableActualWriteIsZeroNumber;
    }

    public MutableGraph<String> getGraph() {
        return graph;
    }

    public void setGraph(MutableGraph<String> graph) {
        this.graph = graph;
    }

    public String getDagId() {
        return dagId;
    }

    public String getTableId() {
        return tableId;
    }

    public String getTableName() {
        return tableName;
    }

    public int getActualWrite() {
        return actualWrite;
    }

    public static class Builder{
        private String dagId;
        private String tableId;
        private String tableName;
        private int actualWrite;
        public Builder() {}

        public Builder setDagId(String dagId) {
            this.dagId = dagId;
            return this;
        }

        public Builder setTableId(String tableId) {
            this.tableId = tableId;
            return this;
        }

        public Builder setTableName(String tableName) {
            this.tableName = tableName;
            return this;
        }

        public Builder setActualWrite(int actualWrite) {
            this.actualWrite = actualWrite;
            return this;
        }
        public UpdateNode build() {
            return new UpdateNode(this);
        }
    }
}
