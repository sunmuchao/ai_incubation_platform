package updateBlood;

import com.google.common.graph.MutableGraph;

import java.util.HashMap;
import java.util.Map;

public class UpdateNetwork {
    private MutableGraph<String> graph;
    private Map<String,String> parentChildRelationship;

    UpdateNetwork(MutableGraph<String> graph){
        this.graph = graph;
        parentChildRelationship = new HashMap<>();
    }

    public MutableGraph<String> getGraph() {
        return graph;
    }

    public void setGraph(MutableGraph<String> graph) {
        this.graph = graph;
    }

    public Map<String, String> getParentChildRelationship() {
        return parentChildRelationship;
    }

    public void addParentChildRelationship(String preTableIds, String tableId) {
        parentChildRelationship.put(preTableIds, tableId);
    }
}