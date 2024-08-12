package updateBlood.UpdateProcessor;

import com.google.common.graph.MutableGraph;

import java.io.IOException;
import java.sql.SQLException;
import java.text.ParseException;
import java.util.List;

/**
 * @author sunmuchao
 * @date 2023/7/19 2:09 下午
 */
public interface UpdateProcessor {
    StringBuffer process(MutableGraph<String> graph, List<String[]> csvList, String dagid) throws IOException, ParseException, SQLException;
}
