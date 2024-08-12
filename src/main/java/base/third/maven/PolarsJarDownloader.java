package base.third.maven;

public class PolarsJarDownloader {
    public static void main(String[] args) {
        JarVersion jarVersion = MavenUtils.getJarVersion("polars-assembly");
        System.out.println(jarVersion);
        String url = "http://mvn.finedevelop.com/repository/fanruan/"+jarVersion.getPath();
        String currentDir = System.getProperty("user.dir");
        System.out.println(currentDir);
        MavenUtils.downloadJar(url,currentDir,"polars.jar");
    }
}
