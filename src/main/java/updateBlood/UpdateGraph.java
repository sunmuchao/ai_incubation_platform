package updateBlood;

import com.google.common.graph.MutableGraph;

import java.util.HashSet;
import java.util.Set;

public class UpdateGraph {
    private String dagId;
    private MutableGraph<String> graph;
    private Set<UpdateNode> updateNodes;

    UpdateGraph(String dagId, MutableGraph<String> graph){
        this.dagId = dagId;
        this.graph = graph;
        this.updateNodes = new HashSet<>();
    }

    public String getDagId() {
        return dagId;
    }

    public void setDagId(String dagId) {
        this.dagId = dagId;
    }

    public MutableGraph<String> getGraph() {
        return graph;
    }

    public void setGraph(MutableGraph<String> graph) {
        this.graph = graph;
    }

    public Set<UpdateNode> getUpdateNodes() {
        return updateNodes;
    }
}
