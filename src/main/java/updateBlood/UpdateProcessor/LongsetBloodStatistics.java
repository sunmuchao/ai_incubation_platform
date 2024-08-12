/*
package updateBlood.UpdateProcessor;

import com.google.common.graph.MutableGraph;
import updateBlood.GraphUtils;

import java.io.IOException;
import java.sql.SQLException;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.Map;

*/
/**
 * @author sunmuchao
 * @date 2023/7/19 4:06 下午
 *//*

public class LongsetBloodStatistics implements UpdateProcessor {
    private GraphUtils graphUtils;
    private Map<String,Integer> csvMapping;
    public LongsetBloodStatistics(GraphUtils graphUtils, Map<String,Integer> csvMapping) {
        this.graphUtils = graphUtils;
        this.csvMapping = csvMapping;
    }

    @Override
    public StringBuffer process(MutableGraph<String> graph, List<String[]> csvList, String dagid) throws IOException, ParseException, SQLException {
        StringBuffer sql = new StringBuffer();
        int maxNodeCount = graphUtils.longestBloodline(graph, 0);
        sql.append("INSERT INTO nonSkipUpdatesLongestBlood (time, dagid, maxNodeCount) VALUES('" +  new SimpleDateFormat("YYYY-MM-dd").format(new Date()) + "','"  + dagid + "'," + maxNodeCount + ");\n");
        System.out.println("INSERT INTO nonSkipUpdatesLongestBlood (time, dagid, maxNodeCount) VALUES('" +  new SimpleDateFormat("YYYY-MM-dd").format(new Date()) + "','"  + dagid + "'," + maxNodeCount + ");\n");
        return sql;
    }
}
*/
