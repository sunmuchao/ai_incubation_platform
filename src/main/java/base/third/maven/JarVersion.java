package base.third.maven;


import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@AllArgsConstructor
@NoArgsConstructor
public class JarVersion {
    private String format;
    private String group;
    private String id;
    private String name;
    private String repositoryName;
    private String version;
    private long time;
    private String path;


}
