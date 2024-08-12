/*
package updateBlood.UpdateProcessor;

import com.google.common.graph.MutableGraph;
import updateBlood.GraphUtils;
import updateBlood.PathContent;
import updateBlood.PathContent.RootPath;

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
 * @date 2023/7/19 3:16 下午
 *//*

public class LayerWidthStatistics implements UpdateProcessor {
    private GraphUtils graphUtils;
    private Map<String,Integer> csvMapping;
    public LayerWidthStatistics(GraphUtils graphUtils, Map<String,Integer> csvMapping) {
        this.graphUtils = graphUtils;
        this.csvMapping = csvMapping;
    }

    @Override
    public StringBuffer process(MutableGraph<String> graph, List<String[]> csvList, String dagid) throws IOException, ParseException, SQLException {
        StringBuffer sql = new StringBuffer();
        PathContent path = graphUtils.getAllLayerWidth(graph);
        for (RootPath rootpath : path.updateLinks) {
            int layer = 1;
            for (Integer nonSkipUpdatesLayerLayerWidth : rootpath.nonSkipUpdatesLayerWidth) {
                if (nonSkipUpdatesLayerLayerWidth != 0) {
                    sql.append("INSERT INTO nonSkipUpdatesLayerWidth (time, dagid, tableid, layer, width) VALUES('" + new SimpleDateFormat("YYYY-MM-dd").format(new Date())
                            + "','"  + dagid + "','" + rootpath.getRoot() + "'," + layer++ + "," + nonSkipUpdatesLayerLayerWidth + "" + ");\n");
                    System.out.println("INSERT INTO nonSkipUpdatesLayerWidth (time, dagid, tableid, layer, width) VALUES('" + new SimpleDateFormat("YYYY-MM-dd").format(new Date())
                            + "','"  + dagid + "','" + rootpath.getRoot() + "'," + layer++ + "," + nonSkipUpdatesLayerLayerWidth + "" + ");\n");
                }
            }
        }
        return sql;
    }
}
*/
