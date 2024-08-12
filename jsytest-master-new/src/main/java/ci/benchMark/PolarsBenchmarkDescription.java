package ci.benchMark;

import com.moandjiezana.toml.Toml;
import com.moandjiezana.toml.TomlWriter;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * @author sunmuchao
 * @date 2024/7/4 2:00 下午
 */
public class PolarsBenchmarkDescription {
    private static final Logger LOGGER = LoggerFactory.getLogger(PolarsBenchmarkDescription.class);
    private final String id;
    private final String name;
    private final String category;


    private final String dataSet;
    private final List<String> tags;
    private final long creationTimestamp;
    private final String comment;
    private final List<String> dependenceIds;
    private final List<String> relatedIds;
    private final Map<String, Float> weights;
    private final String pls;
    private final Map<String, String> sqls;


    public PolarsBenchmarkDescription(String id, String name, String category, String dataSet, List<String> tags,
                                      long creationTimestamp,
                                      String comment, List<String> dependenceIds, List<String> relatedIds,
                                      Map<String, Float> weights, String pls, Map<String, String> sqls) {
        this.id = id;
        this.name = name;
        this.category = category;
        this.dataSet = dataSet;
        this.tags = tags;
        this.creationTimestamp = creationTimestamp;
        this.comment = comment;
        this.dependenceIds = dependenceIds;
        this.relatedIds = relatedIds;
        this.weights = weights;
        this.pls = pls;
        this.sqls = sqls;
    }

    public String getId() {
        return id;
    }

    public String getName() {
        return name;
    }

    public String getCategory() {
        return category;
    }

    public List<String> getTags() {
        return tags;
    }

    public long getCreationTimestamp() {
        return creationTimestamp;
    }

    public String getComment() {
        return comment;
    }

    public List<String> getDependenceIds() {
        return dependenceIds;
    }

    public Map<String, Float> getWeights() {
        return weights;
    }

    public String getPls() {
        return pls;
    }


    public String getDataSet() {
        return dataSet;
    }

    public List<String> getRelatedIds() {
        return relatedIds;
    }

    public Map<String, String> getSqls() {
        return sqls;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        PolarsBenchmarkDescription that = (PolarsBenchmarkDescription) o;
        return creationTimestamp == that.creationTimestamp && Objects.equals(id,
                that.id) && Objects.equals(
                name, that.name) && Objects.equals(category, that.category) && Objects.equals(dataSet,
                that.dataSet) && Objects.equals(
                tags, that.tags) && Objects.equals(comment, that.comment) && Objects.equals(
                dependenceIds, that.dependenceIds) && Objects.equals(relatedIds,
                that.relatedIds) && Objects.equals(
                weights, that.weights) && Objects.equals(pls, that.pls) && Objects.equals(sqls, that.sqls);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, category, dataSet, tags, creationTimestamp, comment, dependenceIds, relatedIds,
                weights, pls, sqls);
    }

    @Override
    public String toString() {
        final StringBuffer sb = new StringBuffer();
        sb.append("id:'").append(id).append('\'');
        sb.append(", name:'").append(name).append('\'');
        sb.append(", category:'").append(category).append('\'');
        sb.append(", dataSet:'").append(dataSet).append('\'');
        sb.append(", tags:").append(tags);
        sb.append(", creationTimestamp:").append(creationTimestamp);
        sb.append(", comment:'").append(comment).append('\'');
        sb.append(", dependenceIds:").append(dependenceIds);
        sb.append(", relatedIds:").append(relatedIds);
        sb.append(", weights:").append(weights);
        sb.append(", pls:'").append(pls).append('\'');
        sb.append(", sqls:'").append(sqls).append('\'');
        return sb.toString();
    }

    public static void writeToFile(PolarsBenchmarkDescription benchmark, String filePath) throws IOException {
        TomlWriter writer = new TomlWriter();
        String tomlString = writer.write(benchmark);
        try (FileWriter fileWriter = new FileWriter(filePath)) {
            fileWriter.write(tomlString);
        }
    }

    public static PolarsBenchmarkDescription readFromFile(String filePath) throws IOException {
        Toml toml = new Toml().read(new File(filePath));
        return toml.to(PolarsBenchmarkDescription.class);
    }
}
