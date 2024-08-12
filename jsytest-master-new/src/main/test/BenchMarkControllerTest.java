import ci.benchMark.BenchMarkController;
import org.junit.Test;

import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * @author sunmuchao
 * @date 2024/8/9 5:24 下午
 */
public class BenchMarkControllerTest {
    @Test
    public void testResultToDB() throws Exception {
        Path workPath = Paths.get("");
        BenchMarkController.ResultToDB(workPath, "polars");
    }
}
