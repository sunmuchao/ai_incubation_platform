package ci.benchMarkCluster;

public class Cluster {
    private String name;
    private boolean state;
    private String id;

    public Cluster() {
    }

    public Cluster(String name, boolean state, String id) {
        this.name = name;
        this.state = state;
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public boolean getState() {
        return state;
    }

    public String getId() {
        return id;
    }

    @Override
    public String toString() {
        return "{" +
                "name='" + name + '\'' +
                ", id='" + id + '\'' +
                '}';
    }
}
